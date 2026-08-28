"""Importação corporativa de colaboradores.

O arquivo de colaboradores não é fonte de verdade de centros. Cada carga
pertence à empresa escolhida e apenas resolve ``empresa_id + centro_id``.
"""
from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Thread
from time import time
from uuid import uuid4

from flask import current_app, jsonify, request
from sqlalchemy import text

from import_col.cadInBd import (
    create_cost_centers,
    create_employees,
    ensure_positions,
    latest_employees,
    link_supervisors_to_employees,
    validate_cost_center_identities,
)
from models.empresas import Company
from models.importacao_colaboradores import CollaboratorImportLog
from models.usuarios import Users
from services.employee_spreadsheet_parser import parse_employee_spreadsheet
from utils.db import db
from utils.filial_scope import is_admin
from utils.safe_route import safe_route
from utils.socket import socketio


MAX_IMPORT_SIZE = 100 * 1024 * 1024
MAX_CHUNK_SIZE = 768 * 1024
JOB_TTL_SECONDS = 60 * 60
UPLOAD_ROOT = Path(tempfile.gettempdir()) / "tmhub-importacao-colaboradores"
_jobs: dict[str, dict] = {}
_jobs_lock = Lock()


def _snapshot(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def _update(job_id: str, **values):
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(values)
            _jobs[job_id]["updated_at"] = time()
    _update_log(job_id, **values)


def _update_log(job_id: str, **values):
    log = CollaboratorImportLog.query.filter_by(job_id=job_id).first()
    if not log:
        return
    fields = {
        "status", "phase", "total", "processados", "colaboradores_criados",
        "colaboradores_atualizados", "colaboradores_ignorados", "cargos_criados",
        "registros_invalidos", "duplicidades", "erro",
    }
    for key, value in values.items():
        target = "fase" if key == "phase" else key
        if key in fields and hasattr(log, target):
            setattr(log, target, value)
    log.atualizado_em = datetime.now(timezone.utc)
    if values.get("status") in {"completed", "error"}:
        log.finalizado_em = datetime.now(timezone.utc)
    db.session.commit()


def _create_log(job_id, company, origin, total, invalid, duplicates, user_id=None, filename=None):
    user = db.session.get(Users, user_id) if user_id else None
    db.session.add(CollaboratorImportLog(
        job_id=job_id,
        origem=origin,
        empresa_id=company.id,
        empresa_nome=company.nome,
        usuario_id=user.id if user else None,
        usuario_nome=user.nome if user else None,
        arquivo=filename,
        status="queued",
        fase="preparando",
        total=total,
        registros_invalidos=len(invalid),
        duplicidades=duplicates,
    ))
    db.session.commit()


def _cleanup():
    cutoff = time() - JOB_TTL_SECONDS
    with _jobs_lock:
        expired = [job_id for job_id, job in _jobs.items() if job.get("updated_at", 0) < cutoff]
        for job_id in expired:
            _jobs.pop(job_id, None)
            shutil.rmtree(UPLOAD_ROOT / job_id, ignore_errors=True)


def _selected_company(value) -> Company:
    if value in (None, ""):
        raise ValueError("Selecione a empresa antes de importar os colaboradores.")
    try:
        company = db.session.get(Company, int(value))
    except (TypeError, ValueError):
        name = " ".join(str(value).strip().split()).upper()
        company = Company.query.filter(db.func.upper(Company.nome) == name).first()
    if not company or not company.ativa:
        raise ValueError("Selecione uma empresa ativa já cadastrada no sistema.")
    return company


def _company_catalog(records):
    if not isinstance(records, list) or not records:
        raise ValueError("Envie 'empresas' como uma lista não vazia.")
    if len(records) > 1000:
        raise ValueError("Cada carga pode conter no máximo 1.000 empresas.")
    companies = {}
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"Empresa {index}: conteúdo inválido.")
        try:
            company_id = int(record.get("id", record.get("empresa_id")))
        except (TypeError, ValueError) as error:
            raise ValueError(f"Empresa {index}: ID e nome são obrigatórios.") from error
        name = " ".join(str(record.get("nome", record.get("empresa_nome")) or "").split()).upper()
        if company_id <= 0 or not name:
            raise ValueError(f"Empresa {index}: ID e nome são obrigatórios.")
        previous = companies.get(company_id)
        if previous and previous != name:
            raise ValueError(
                f"Empresa {company_id}: nomes divergentes na mesma carga "
                f"('{previous}' e '{name}')."
            )
        companies[company_id] = name
    return companies


def _prepare(path: Path, filename: str, company: Company):
    if path.suffix.lower() not in {".xls", ".xlsx"}:
        raise ValueError("Envie o relatório no formato .xls ou .xlsx.")
    parsed = parse_employee_spreadsheet(path, filename)
    for employee in parsed["employees"]:
        employee["empresa_nome"] = company.nome
        employee["_empresa_id"] = company.id
    employees, dedupe_errors, duplicates = latest_employees(parsed["employees"])
    validate_cost_center_identities(employees)
    return employees, [*parsed["invalid"], *dedupe_errors], duplicates


def _prepare_data(records, company: Company):
    if not isinstance(records, list):
        raise ValueError("Envie 'colaboradores' como uma lista.")
    if not records:
        raise ValueError("A lista de colaboradores está vazia.")
    if len(records) > 50000:
        raise ValueError("Cada carga pode conter no máximo 50.000 colaboradores.")

    prepared = []
    invalid = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            invalid.append(f"Registro {index}: conteúdo inválido.")
            continue
        employee = dict(record)
        employee["codigo"] = employee.get("codigo", employee.get("matricula"))
        employee["admissao"] = employee.get("admissao", employee.get("data_admissao"))
        employee["centro_custo_num"] = employee.get(
            "centro_custo_num", employee.get("codigo_centro_custo")
        )
        employee["hor"] = employee.get("hor", employee.get("carga_horaria"))
        employee["empresa_nome"] = company.nome
        employee["_empresa_id"] = company.id
        if not str(employee.get("nome") or "").strip():
            invalid.append(f"Registro {index}: nome não informado.")
            continue
        prepared.append(employee)

    employees, dedupe_errors, duplicates = latest_employees(prepared)
    validate_cost_center_identities(employees)
    return employees, [*invalid, *dedupe_errors], duplicates


def _emit(job_id: str, severity: str, summary: str, detail: str, changed=False):
    job = _snapshot(job_id) or {}
    try:
        if changed:
            socketio.emit("data_changed", {
                "channel": "colaboradores", "resource": "colaboradores",
                "action": "import_completed", "user_id": job.get("user_id"),
            })
        if job.get("user_id") is not None:
            socketio.emit("system_notification", {
                "severity": severity, "summary": summary, "detail": detail, "job_id": job_id,
            }, to=f"user:{job['user_id']}")
    except Exception:
        pass


def _run(app, job_id: str, employees: list[dict], invalid: list[str], duplicates: int):
    with app.app_context():
        try:
            _update(job_id, status="processing", phase="cargos")
            with db.engine.begin() as connection:
                positions, positions_created = ensure_positions(connection, employees)
                _update(job_id, phase="centros", cargos_criados=positions_created)
                # Centros vêm da tela própria: esta etapa somente resolve a FK.
                create_cost_centers(connection, employees, sync_catalog=False)
                _update(job_id, phase="colaboradores")
                total = len(employees)

                def progress(processed):
                    if processed % 100 == 0 or processed == total:
                        _update(job_id, processados=processed, percentual=round(processed / total * 100, 2) if total else 100)

                created, updated, ignored = create_employees(connection, employees, positions, progress)
                _update(job_id, phase="supervisores")
                linked, unresolved = link_supervisors_to_employees(connection, employees)

            _update(job_id, status="completed", phase="concluido", processados=len(employees), percentual=100,
                    colaboradores_criados=created, colaboradores_atualizados=updated,
                    colaboradores_ignorados=ignored, cargos_criados=positions_created,
                    supervisores_vinculados=linked, supervisores_nao_encontrados=unresolved,
                    registros_invalidos=len(invalid), duplicidades=duplicates, erros=invalid[:20])
            _emit(job_id, "success", "Importação concluída", f"{len(employees)} colaboradores foram processados.", changed=True)
        except Exception as error:
            _update(job_id, status="error", phase="erro", erro=str(error))
            _emit(job_id, "error", "Erro na importação", str(error))


def _queue(
    employees, invalid, duplicates, company: Company, job_id=None, user_id=None,
    *, origin="sistema", filename=None,
):
    job_id = job_id or uuid4().hex
    now = time()
    with _jobs_lock:
        current = _jobs.get(job_id, {})
        _jobs[job_id] = {**current, "id": job_id, "status": "queued", "phase": "preparando",
                         "total": len(employees), "processados": 0, "percentual": 0,
                         "registros_invalidos": len(invalid), "duplicidades": duplicates,
                         "empresa_id": company.id, "empresa_nome": company.nome,
                         "user_id": current.get("user_id", user_id),
                         "created_at": current.get("created_at", now), "updated_at": now}
    _create_log(
        job_id, company, origin, len(employees), invalid, duplicates,
        user_id=user_id if origin == "sistema" else None,
        filename=filename,
    )
    app = current_app._get_current_object()
    Thread(target=_run, args=(app, job_id, employees, invalid, duplicates), daemon=True,
           name=f"importacao-colaboradores-{job_id[:8]}").start()
    return _snapshot(job_id)


class CollaboratorImportService:
    @safe_route
    def companies(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem consultar empresas."), 403
        return jsonify([{"id": item.id, "nome": item.nome, "ativa": bool(item.ativa)}
                        for item in Company.query.order_by(Company.ativa.desc(), Company.nome).all()]), 200

    @safe_route
    def sync_companies(self, token_data):
        """Sincroniza IDs e nomes corporativos antes da carga automática."""
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem sincronizar empresas."), 403
        data = request.get_json(silent=True) or {}
        try:
            companies = _company_catalog(data.get("empresas"))
        except ValueError as error:
            return jsonify(str(error) or "Existem empresas inválidas na carga."), 400

        ids = sorted(companies)
        existing_by_id = {
            company.id: company
            for company in Company.query.filter(Company.id.in_(ids)).all()
        }
        existing_by_name = {
            company.nome.upper(): company
            for company in Company.query.filter(
                db.func.upper(Company.nome).in_(list(companies.values()))
            ).all()
        }
        for company_id, name in companies.items():
            same_name = existing_by_name.get(name)
            if same_name and same_name.id != company_id:
                return jsonify(
                    f"A empresa '{name}' já está cadastrada com o ID {same_name.id}; "
                    f"a origem enviou o ID {company_id}."
                ), 409

        created = updated = ignored = 0
        for company_id, name in companies.items():
            company = existing_by_id.get(company_id)
            if company is None:
                db.session.add(Company(id=company_id, nome=name, ativa=True))
                created += 1
            elif company.nome != name or not company.ativa:
                company.nome = name
                company.ativa = True
                updated += 1
            else:
                ignored += 1
        db.session.flush()
        if created:
            db.session.execute(text(
                "SELECT setval(pg_get_serial_sequence('empresas', 'id'), "
                "(SELECT MAX(id) FROM empresas), true)"
            ))
        db.session.commit()
        return jsonify({
            "total": len(companies),
            "empresas_criadas": created,
            "empresas_atualizadas": updated,
            "empresas_ignoradas": ignored,
        }), 200

    @safe_route
    def create(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem importar colaboradores."), 403
        uploaded = request.files.get("file")
        if not uploaded or Path(uploaded.filename).suffix.lower() not in {".xls", ".xlsx"}:
            return jsonify("Envie o relatório padrão em .xls ou .xlsx."), 400
        if request.content_length and request.content_length > MAX_IMPORT_SIZE:
            return jsonify("O arquivo deve ter no máximo 100 MB."), 413
        try:
            company = _selected_company(request.form.get("empresa_id") or request.form.get("empresa_nome"))
            with tempfile.NamedTemporaryFile(suffix=Path(uploaded.filename).suffix, delete=False) as temporary:
                temporary.write(uploaded.read())
                file_path = Path(temporary.name)
            try:
                employees, invalid, duplicates = _prepare(file_path, uploaded.filename, company)
            finally:
                file_path.unlink(missing_ok=True)
        except (OSError, TypeError, ValueError) as error:
            return jsonify(f"Não foi possível ler o arquivo: {error}"), 400
        if not employees:
            return jsonify("O arquivo não contém colaboradores válidos."), 400
        _cleanup()
        return jsonify(_queue(
            employees, invalid, duplicates, company,
            user_id=token_data.get("id"), origin="sistema", filename=uploaded.filename,
        )), 202

    @safe_route
    def create_from_data(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem importar colaboradores."), 403
        data = request.get_json(silent=True) or {}
        try:
            company = _selected_company(data.get("empresa_id") or data.get("empresa_nome"))
            employees, invalid, duplicates = _prepare_data(
                data.get("colaboradores", data.get("employees")), company
            )
        except (TypeError, ValueError) as error:
            return jsonify(f"Não foi possível preparar os colaboradores: {error}"), 400
        if not employees:
            return jsonify("A carga não contém colaboradores válidos."), 400
        _cleanup()
        return jsonify(_queue(
            employees, invalid, duplicates, company,
            origin="script", filename=data.get("identificador") or "sc.py",
        )), 202

    @safe_route
    def history(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem consultar importações."), 403
        try:
            limit = min(max(int(request.args.get("limit", 20)), 1), 100)
        except (TypeError, ValueError):
            limit = 20
        rows = (
            CollaboratorImportLog.query
            .order_by(CollaboratorImportLog.iniciado_em.desc(), CollaboratorImportLog.id.desc())
            .limit(limit)
            .all()
        )
        return jsonify([row.to_dict() for row in rows]), 200

    @safe_route
    def start_upload(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem importar colaboradores."), 403
        data = request.get_json(silent=True) or {}
        filename = str(data.get("filename") or "")
        try:
            size, chunks = int(data.get("size") or 0), int(data.get("chunks") or 0)
            company = _selected_company(data.get("empresa_id") or data.get("empresa_nome"))
        except (TypeError, ValueError) as error:
            return jsonify(str(error) or "Dados de importação inválidos."), 400
        if Path(filename).suffix.lower() not in {".xls", ".xlsx"}:
            return jsonify("Envie o relatório padrão em .xls ou .xlsx."), 400
        if size <= 0 or size > MAX_IMPORT_SIZE:
            return jsonify("O arquivo deve ter no máximo 100 MB."), 413
        if chunks <= 0:
            return jsonify("Quantidade de partes inválida."), 400
        _cleanup(); job_id = uuid4().hex; now = time(); (UPLOAD_ROOT / job_id).mkdir(parents=True, exist_ok=False)
        with _jobs_lock:
            _jobs[job_id] = {"id": job_id, "status": "uploading", "phase": "upload", "filename": filename,
                             "empresa_id": company.id, "empresa_nome": company.nome, "file_size": size,
                             "chunks": chunks, "chunks_recebidos": [], "bytes_recebidos": 0,
                             "percentual_upload": 0, "user_id": token_data.get("id"),
                             "created_at": now, "updated_at": now}
        return jsonify(_snapshot(job_id)), 201

    @safe_route
    def upload_chunk(self, job_id, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem importar colaboradores."), 403
        job = _snapshot(job_id)
        if not job or job.get("status") != "uploading":
            return jsonify("Envio não encontrado ou já finalizado."), 404
        uploaded = request.files.get("chunk")
        try: index = int(request.form.get("index", -1))
        except (TypeError, ValueError): index = -1
        if not uploaded or not 0 <= index < job["chunks"]:
            return jsonify("Parte do arquivo inválida."), 400
        content = uploaded.read(MAX_CHUNK_SIZE + 1)
        if len(content) > MAX_CHUNK_SIZE:
            return jsonify("Parte do arquivo excede o limite permitido."), 413
        (UPLOAD_ROOT / job_id / f"{index:06d}.part").write_bytes(content)
        with _jobs_lock:
            current = _jobs[job_id]; received = set(current["chunks_recebidos"]); received.add(index)
            current["chunks_recebidos"] = sorted(received)
            current["bytes_recebidos"] = sum(part.stat().st_size for part in (UPLOAD_ROOT / job_id).glob("*.part"))
            current["percentual_upload"] = round(min(100, current["bytes_recebidos"] / current["file_size"] * 100), 2)
            current["updated_at"] = time()
        return jsonify(_snapshot(job_id)), 200

    @safe_route
    def complete_upload(self, job_id, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem importar colaboradores."), 403
        job = _snapshot(job_id)
        if not job or job.get("status") != "uploading":
            return jsonify("Envio não encontrado ou já finalizado."), 404
        if len(job["chunks_recebidos"]) != job["chunks"]:
            return jsonify("Ainda existem partes do arquivo pendentes."), 409
        directory = UPLOAD_ROOT / job_id; output = directory / f"arquivo{Path(job['filename']).suffix.lower()}"
        try:
            with output.open("wb") as stream:
                for index in range(job["chunks"]): stream.write((directory / f"{index:06d}.part").read_bytes())
            if output.stat().st_size != job["file_size"]: raise ValueError("O arquivo recebido está incompleto.")
            company = _selected_company(job["empresa_id"])
            employees, invalid, duplicates = _prepare(output, job["filename"], company)
        except (OSError, TypeError, ValueError) as error:
            return jsonify(f"Não foi possível ler o arquivo: {error}"), 400
        finally:
            shutil.rmtree(directory, ignore_errors=True)
        if not employees: return jsonify("O arquivo não contém colaboradores válidos."), 400
        return jsonify(_queue(
            employees, invalid, duplicates, company, job_id, token_data.get("id"),
            origin="sistema", filename=job.get("filename"),
        )), 202

    @safe_route
    def read(self, job_id, token_data):
        if not is_admin(token_data): return jsonify("Apenas administradores podem acompanhar importações."), 403
        job = _snapshot(job_id)
        if job:
            return jsonify(job), 200
        persisted = CollaboratorImportLog.query.filter_by(job_id=job_id).first()
        return (jsonify(persisted.to_dict()), 200) if persisted else (jsonify("Importação não encontrada ou expirada."), 404)
