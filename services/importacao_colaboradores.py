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
    ensure_positions,
    latest_employees,
    link_supervisors_to_employees,
)
from import_col.json_loader import prepare_uploaded_json
from utils.db import db
from utils.filial_scope import is_admin
from utils.safe_route import safe_route
from utils.socket import socketio


MAX_JSON_SIZE = 60 * 1024 * 1024
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


def _create_processing_job(employees, invalid, duplicates, job_id=None, user_id=None):
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
            "user_id": current.get("user_id", user_id),
            "created_at": current.get("created_at", now),
            "updated_at": now,
        }
    app = current_app._get_current_object()
    Thread(
        target=_run_import,
        args=(app, job_id, employees, invalid, duplicates),
        daemon=True,
        name=f"importacao-colaboradores-{job_id[:8]}",
    ).start()
    return _job_snapshot(job_id)


def _run_import(app, job_id, employees, invalid, duplicates):
    with app.app_context():
        try:
            _update_job(job_id, status="processing", phase="cargos")
            with db.engine.begin() as connection:
                positions, positions_created = ensure_positions(connection, employees)
                _update_job(job_id, phase="centros", cargos_criados=positions_created)
                centers_created, centers_updated = create_cost_centers(connection, employees)
                _update_job(
                    job_id,
                    phase="colaboradores",
                    centros_criados=centers_created,
                    centros_atualizados=centers_updated,
                )

                total = len(employees)

                def progress(processed):
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


class CollaboratorImportService:
    @safe_route
    def create(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem importar colaboradores."), 403

        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename.lower().endswith(".json"):
            return jsonify("Envie o relatório no formato .json."), 400
        if request.content_length and request.content_length > MAX_JSON_SIZE:
            return jsonify("O arquivo JSON deve ter no máximo 60 MB."), 413

        try:
            payload = json.load(uploaded.stream)
            employees, invalid, duplicates = latest_employees(
                prepare_uploaded_json(payload)
            )
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
            return jsonify(f"Não foi possível ler o JSON: {error}"), 400
        if not employees:
            return jsonify("O JSON não contém colaboradores válidos."), 400

        _cleanup_jobs()
        return jsonify(_create_processing_job(
            employees,
            invalid,
            duplicates,
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
        if not filename.lower().endswith(".json"):
            return jsonify("Envie o relatório no formato .json."), 400
        if size <= 0 or size > MAX_JSON_SIZE:
            return jsonify("O arquivo JSON deve ter no máximo 60 MB."), 413
        if chunks <= 0:
            return jsonify("Quantidade de partes inválida."), 400

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
        assembled_path = upload_dir / "arquivo.json"
        try:
            with assembled_path.open("wb") as assembled:
                for index in range(job["chunks"]):
                    assembled.write((upload_dir / f"{index:06d}.part").read_bytes())
            if assembled_path.stat().st_size != job["file_size"]:
                return jsonify("O arquivo recebido está incompleto."), 409
            with assembled_path.open("r", encoding="utf-8-sig") as stream:
                payload = json.load(stream)
            employees, invalid, duplicates = latest_employees(
                prepare_uploaded_json(payload)
            )
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
            return jsonify(f"Não foi possível ler o JSON: {error}"), 400
        finally:
            shutil.rmtree(upload_dir, ignore_errors=True)
        if not employees:
            return jsonify("O JSON não contém colaboradores válidos."), 400

        return jsonify(
            _create_processing_job(
                employees,
                invalid,
                duplicates,
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
