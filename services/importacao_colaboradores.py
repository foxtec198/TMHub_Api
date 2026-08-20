# Regras de negócio de importação de colaboradores.
# Biblioteca padrão.
import json
import shutil
import tempfile
from pathlib import Path
from threading import Lock, Thread
from time import time
from uuid import uuid4

# Dependências externas.
from flask import current_app, jsonify, request

# Módulos internos da aplicação.
from import_col.cadInBd import (
    create_cost_centers,
    create_employees,
    ensure_companies,
    ensure_positions,
    latest_employees,
    link_supervisors_to_employees,
    normalize_name,
    validate_cost_center_identities,
)
from import_col.json_loader import prepare_uploaded_json
from models.empresas import Company
from services.employee_spreadsheet_parser import parse_employee_spreadsheet
from utils.db import db
from utils.filial_scope import is_admin
from utils.safe_route import safe_route
from utils.socket import socketio


MAX_IMPORT_SIZE = 100 * 1024 * 1024
MAX_CHUNK_SIZE = 768 * 1024
JOB_TTL_SECONDS = 60 * 60
UPLOAD_ROOT = Path(tempfile.gettempdir()) / "tmhub-importacao-colaboradores"
_jobs = {}
_jobs_lock = Lock()


def _job_snapshot(job_id):
    with _jobs_lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def _update_job(job_id, **values):
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(values)
            _jobs[job_id]["updated_at"] = time()


def _cleanup_jobs():
    cutoff = time() - JOB_TTL_SECONDS
    with _jobs_lock:
        expired = [
            job_id for job_id, job in _jobs.items()
            if job.get("updated_at", 0) < cutoff
        ]
        for job_id in expired:
            _jobs.pop(job_id, None)
            shutil.rmtree(UPLOAD_ROOT / job_id, ignore_errors=True)


def _emit_import_outcome(job_id, severity, summary, detail, broadcast_change=False):
    job = _job_snapshot(job_id)
    try:
        if broadcast_change:
            socketio.emit(
                "data_changed",
                {
                    "channel": "colaboradores",
                    "resource": "colaboradores",
                    "action": "import_completed",
                    "user_id": job.get("user_id") if job else None,
                },
            )
        if job and job.get("user_id") is not None:
            socketio.emit(
                "system_notification",
                {
                    "severity": severity,
                    "summary": summary,
                    "detail": detail,
                    "job_id": job_id,
                },
                to=f"user:{job['user_id']}",
            )
    except Exception:
        # The committed import result remains authoritative even if the
        # realtime transport is temporarily unavailable.
        return


def _create_processing_job(
    employees,
    invalid,
    duplicates,
    company_name,
    *,
    sync_catalog=False,
    job_id=None,
    user_id=None,
):
    job_id = job_id or uuid4().hex
    now = time()
    with _jobs_lock:
        current = _jobs.get(job_id, {})
        _jobs[job_id] = {
            **current,
            "id": job_id,
            "status": "queued",
            "phase": "preparando",
            "total": len(employees),
            "processados": 0,
            "percentual": 0,
            "registros_invalidos": len(invalid),
            "duplicidades": duplicates,
            "empresas": [company_name],
            "empresa_nome": company_name,
            "sincronizar_catalogo_centros": bool(sync_catalog),
            "user_id": current.get("user_id", user_id),
            "created_at": current.get("created_at", now),
            "updated_at": now,
        }
    app = current_app._get_current_object()
    Thread(
        target=_run_import,
        args=(app, job_id, employees, invalid, duplicates, bool(sync_catalog)),
        daemon=True,
        name=f"importacao-colaboradores-{job_id[:8]}",
    ).start()
    return _job_snapshot(job_id)


def _run_import(app, job_id, employees, invalid, duplicates, sync_catalog=False):
    with app.app_context():
        try:
            _update_job(job_id, status="processing", phase="cargos")
            with db.engine.begin() as connection:
                _, companies_created = ensure_companies(connection, employees)
                _update_job(job_id, empresas_criadas=companies_created)
                positions, positions_created = ensure_positions(connection, employees)
                _update_job(job_id, phase="centros", cargos_criados=positions_created)
                centers_created, centers_updated = create_cost_centers(
                    connection,
                    employees,
                    sync_catalog=sync_catalog,
                )
                _update_job(
                    job_id,
                    phase="colaboradores",
                    centros_criados=centers_created,
                    centros_atualizados=centers_updated,
                )

                total = len(employees)

                def progress(processed):
                    if processed % 100 and processed != total:
                        return
                    _update_job(
                        job_id,
                        processados=processed,
                        percentual=round((processed / total) * 100, 2) if total else 100,
                    )

                created, updated, ignored = create_employees(
                    connection,
                    employees,
                    positions=positions,
                    progress_callback=progress,
                )
                _update_job(job_id, phase="supervisores")
                linked, unresolved = link_supervisors_to_employees(connection, employees)

            _update_job(
                job_id,
                status="completed",
                phase="concluido",
                processados=len(employees),
                percentual=100,
                colaboradores_criados=created,
                colaboradores_atualizados=updated,
                colaboradores_ignorados=ignored,
                cargos_criados=positions_created,
                supervisores_vinculados=linked,
                supervisores_nao_encontrados=unresolved,
                registros_invalidos=len(invalid),
                duplicidades=duplicates,
                erros=invalid[:20],
            )
            _emit_import_outcome(
                job_id,
                "success",
                "Importação concluída",
                f"{len(employees)} colaboradores foram processados.",
                broadcast_change=True,
            )
        except Exception as error:
            _update_job(job_id, status="error", phase="erro", erro=str(error))
            _emit_import_outcome(
                job_id,
                "error",
                "Erro na importação",
                str(error),
            )


def _selected_company_name(value):
    company_name = " ".join(str(value or "").strip().split()).upper()
    if not company_name:
        raise ValueError("Selecione a empresa antes de importar os colaboradores.")
    if len(company_name) > 160:
        raise ValueError("O nome da empresa deve ter no máximo 160 caracteres.")
    company = Company.query.filter(
        db.func.upper(Company.nome) == company_name,
        Company.ativa.is_(True),
    ).first()
    if not company:
        raise ValueError("Selecione uma empresa ativa já cadastrada no sistema.")
    return company.nome


def _as_bool(value):
    return str(value or "").strip().lower() in {"1", "true", "sim", "on"}


def _prepare_import_file(file_path, filename, company_name, centro_forcado=None):
    suffix = Path(filename).suffix.lower()
    if suffix == ".json":
        with Path(file_path).open("r", encoding="utf-8-sig") as stream:
            payload = json.load(stream)
        parsed_employees = prepare_uploaded_json(payload)
        invalid = []
    elif suffix in {".xls", ".xlsx"}:
        parsed = parse_employee_spreadsheet(file_path, filename, centro_forcado=centro_forcado)
        parsed_employees = parsed["employees"]
        invalid = list(parsed["invalid"])
    else:
        raise ValueError("Envie o relatório no formato .json, .xls ou .xlsx.")

    source_companies = {
        normalize_name(item.get("empresa_nome"))
        for item in parsed_employees
        if normalize_name(item.get("empresa_nome"))
    }
    if len(source_companies) > 1:
        raise ValueError(
            "O arquivo possui mais de uma empresa identificada. "
            "Envie um arquivo separado para cada empresa."
        )

    # A empresa escolhida no fluxo é a identidade da carga inteira; não
    # deixamos um cabeçalho eventual da planilha misturar empresas no banco.
    for employee in parsed_employees:
        employee["empresa_nome"] = company_name

    employees, dedupe_errors, duplicates = latest_employees(parsed_employees)
    validate_cost_center_identities(employees)
    return employees, [*invalid, *dedupe_errors], duplicates


class CollaboratorImportService:
    @safe_route
    def companies(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem consultar empresas."), 403
        companies = Company.query.order_by(Company.ativa.desc(), Company.nome.asc()).all()
        return jsonify([
            {"id": company.id, "nome": company.nome, "ativa": bool(company.ativa)}
            for company in companies
        ]), 200

    @safe_route
    def create(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem importar colaboradores."), 403

        uploaded = request.files.get("file")
        if not uploaded or Path(uploaded.filename).suffix.lower() not in {".json", ".xls", ".xlsx"}:
            return jsonify("Envie o relatório no formato .json, .xls ou .xlsx."), 400
        if request.content_length and request.content_length > MAX_IMPORT_SIZE:
            return jsonify("O arquivo deve ter no máximo 100 MB."), 413
        try:
            company_name = _selected_company_name(request.form.get("empresa_nome"))
            sync_catalog = _as_bool(request.form.get("sincronizar_catalogo_centros"))
        except ValueError as error:
            return jsonify(str(error)), 400

        try:
            suffix = Path(uploaded.filename).suffix.lower()
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
                temporary.write(uploaded.read())
                temporary_path = Path(temporary.name)
            try:
                employees, invalid, duplicates = _prepare_import_file(
                    temporary_path,
                    uploaded.filename,
                    company_name,
                    request.form.get("centro_forcado"),
                )
            finally:
                temporary_path.unlink(missing_ok=True)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
            return jsonify(f"Não foi possível ler o arquivo: {error}"), 400
        if not employees:
            return jsonify("O arquivo não contém colaboradores válidos."), 400

        _cleanup_jobs()
        return jsonify(_create_processing_job(
            employees,
            invalid,
            duplicates,
            company_name,
            sync_catalog=sync_catalog,
            user_id=token_data.get("id"),
        )), 202

    @safe_route
    def start_upload(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem importar colaboradores."), 403
        data = request.get_json(silent=True) or {}
        filename = str(data.get("filename") or "")
        size = int(data.get("size") or 0)
        chunks = int(data.get("chunks") or 0)
        centro_forcado = data.get("centro_forcado")
        if Path(filename).suffix.lower() not in {".json", ".xls", ".xlsx"}:
            return jsonify("Envie o relatório no formato .json, .xls ou .xlsx."), 400
        if size <= 0 or size > MAX_IMPORT_SIZE:
            return jsonify("O arquivo deve ter no máximo 100 MB."), 413
        if chunks <= 0:
            return jsonify("Quantidade de partes inválida."), 400
        try:
            company_name = _selected_company_name(data.get("empresa_nome"))
            sync_catalog = _as_bool(data.get("sincronizar_catalogo_centros"))
        except ValueError as error:
            return jsonify(str(error)), 400

        _cleanup_jobs()
        job_id = uuid4().hex
        now = time()
        (UPLOAD_ROOT / job_id).mkdir(parents=True, exist_ok=False)
        with _jobs_lock:
            _jobs[job_id] = {
                "id": job_id,
                "status": "uploading",
                "phase": "upload",
                "filename": filename,
                "empresa_nome": company_name,
                "centro_forcado": centro_forcado,
                "sincronizar_catalogo_centros": sync_catalog,
                "file_size": size,
                "chunks": chunks,
                "chunks_recebidos": [],
                "bytes_recebidos": 0,
                "percentual_upload": 0,
                "user_id": token_data.get("id"),
                "created_at": now,
                "updated_at": now,
            }
        return jsonify(_job_snapshot(job_id)), 201

    @safe_route
    def upload_chunk(self, job_id, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem importar colaboradores."), 403
        job = _job_snapshot(job_id)
        if not job or job.get("status") != "uploading": return jsonify("Envio não encontrado ou já finalizado."), 404

        uploaded = request.files.get("chunk")
        try: index = int(request.form.get("index", -1))
        except (TypeError, ValueError): index = -1
        if not uploaded or index < 0 or index >= job["chunks"]: return jsonify("Parte do arquivo inválida."), 400

        content = uploaded.read(MAX_CHUNK_SIZE + 1)
        if len(content) > MAX_CHUNK_SIZE: return jsonify("Parte do arquivo excede o limite permitido."), 413

        part_path = UPLOAD_ROOT / job_id / f"{index:06d}.part"
        part_path.write_bytes(content)
        with _jobs_lock:
            current = _jobs[job_id]
            received = set(current["chunks_recebidos"])
            received.add(index)
            current["chunks_recebidos"] = sorted(received)
            current["bytes_recebidos"] = sum(
                path.stat().st_size for path in (UPLOAD_ROOT / job_id).glob("*.part")
            )
            current["percentual_upload"] = round(
                min(100, current["bytes_recebidos"] / current["file_size"] * 100), 2
            )
            current["updated_at"] = time()
        return jsonify(_job_snapshot(job_id)), 200

    @safe_route
    def complete_upload(self, job_id, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem importar colaboradores."), 403
        job = _job_snapshot(job_id)
        if not job or job.get("status") != "uploading":
            return jsonify("Envio não encontrado ou já finalizado."), 404
        if len(job["chunks_recebidos"]) != job["chunks"]:
            return jsonify("Ainda existem partes do arquivo pendentes."), 409

        upload_dir = UPLOAD_ROOT / job_id
        suffix = Path(job["filename"]).suffix.lower()
        assembled_path = upload_dir / f"arquivo{suffix}"
        try:
            with assembled_path.open("wb") as assembled:
                for index in range(job["chunks"]):
                    assembled.write((upload_dir / f"{index:06d}.part").read_bytes())
            if assembled_path.stat().st_size != job["file_size"]:
                return jsonify("O arquivo recebido está incompleto."), 409
            employees, invalid, duplicates = _prepare_import_file(
                assembled_path,
                job["filename"],
                job.get("empresa_nome"),
                job.get("centro_forcado"),
            )
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
            return jsonify(f"Não foi possível ler o arquivo: {error}"), 400
        finally:
            shutil.rmtree(upload_dir, ignore_errors=True)
        if not employees:
            return jsonify("O arquivo não contém colaboradores válidos."), 400

        return jsonify(
            _create_processing_job(
                employees,
                invalid,
                duplicates,
                job["empresa_nome"],
                sync_catalog=bool(job.get("sincronizar_catalogo_centros")),
                job_id=job_id,
                user_id=token_data.get("id"),
            )
        ), 202

    @safe_route
    def read(self, job_id, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem acompanhar importações."), 403
        job = _job_snapshot(job_id)
        if not job:
            return jsonify("Importação não encontrada ou expirada."), 404
        return jsonify(job), 200
