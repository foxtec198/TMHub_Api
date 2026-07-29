import json
from threading import Lock, Thread
from time import time
from uuid import uuid4

from flask import current_app, jsonify, request

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


MAX_JSON_SIZE = 60 * 1024 * 1024
JOB_TTL_SECONDS = 60 * 60
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
        except Exception as error:
            _update_job(job_id, status="error", phase="erro", erro=str(error))


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
        job_id = uuid4().hex
        now = time()
        with _jobs_lock:
            _jobs[job_id] = {
                "id": job_id,
                "status": "queued",
                "phase": "preparando",
                "total": len(employees),
                "processados": 0,
                "percentual": 0,
                "registros_invalidos": len(invalid),
                "duplicidades": duplicates,
                "created_at": now,
                "updated_at": now,
            }

        app = current_app._get_current_object()
        Thread(
            target=_run_import,
            args=(app, job_id, employees, invalid, duplicates),
            daemon=True,
            name=f"importacao-colaboradores-{job_id[:8]}",
        ).start()
        return jsonify(_job_snapshot(job_id)), 202

    @safe_route
    def read(self, job_id, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem acompanhar importações."), 403
        job = _job_snapshot(job_id)
        if not job:
            return jsonify("Importação não encontrada ou expirada."), 404
        return jsonify(job), 200
