"""Centros de custo: catálogo corporativo, escopo e importação."""
from __future__ import annotations

import tempfile
from pathlib import Path
from threading import Lock, Thread
from time import time
from uuid import uuid4

from flask import current_app, jsonify, request as rq
from sqlalchemy import String, cast, or_, text

from models.centros_de_custo import CostCenters, DepartmentConfiguration
from models.colaboradores import Employees
from models.empresas import Company
from services.cost_center_spreadsheet_parser import parse_cost_center_spreadsheet
from utils.db import db
from utils.filial_scope import allowed_cost_center_ids, apply_cost_center_scope, can_access_cost_center, is_admin, is_matrix_user
from utils.safe_route import safe_route
from utils.socket import socketio

MAX_IMPORT_SIZE = 100 * 1024 * 1024
_imports: dict[str, dict] = {}
_imports_lock = Lock()


def _import_snapshot(job_id):
    with _imports_lock:
        return dict(_imports[job_id]) if job_id in _imports else None


def _update_import(job_id, **values):
    with _imports_lock:
        if job_id in _imports:
            _imports[job_id].update(values)
            _imports[job_id]["updated_at"] = time()


class CostsCenterService:
    @staticmethod
    def _serialize_center(center):
        return {
            "id": center.id, "numero": center.centro_id, "nome": center.nome,
            "local": center.local, "departamento": center.departamento,
            "capacidade_pessoas": center.capacidade_pessoas, "empresa_id": center.empresa_id,
            "empresa_nome": center.empresa.nome if center.empresa else None,
        }

    @staticmethod
    def _company(value):
        try:
            company = db.session.get(Company, int(value))
        except (TypeError, ValueError):
            company = None
        if not company:
            raise LookupError("Empresa não encontrada.")
        if not company.ativa:
            raise ValueError("A empresa selecionada está inativa.")
        return company

    @safe_route
    def companies(self, token_data):
        query = Company.query
        if not (is_admin(token_data) or is_matrix_user(token_data)):
            center_ids = allowed_cost_center_ids(token_data, include_company=False)
            query = query.filter(Company.id.in_(
                db.session.query(CostCenters.empresa_id).filter(CostCenters.id.in_(center_ids or set()))
            ))
        return jsonify([{"id": item.id, "nome": item.nome, "ativa": bool(item.ativa)}
                        for item in query.order_by(Company.ativa.desc(), Company.nome).all()]), 200

    @safe_route
    def read(self, token_data):
        center_id = rq.args.get("id", type=int)
        if center_id:
            if not can_access_cost_center(token_data, center_id):
                return jsonify("Você não possui acesso à filial deste centro de custo."), 403
            center = db.session.get(CostCenters, center_id)
            return (jsonify(self._serialize_center(center)), 200) if center else (jsonify("Centro de custo não encontrado."), 404)

        query = apply_cost_center_scope(CostCenters.query, CostCenters.id, token_data).join(Company)
        requested_ids = {
            int(value)
            for value in str(rq.args.get("ids") or "").split(",")
            if value.strip().isdigit()
        }
        if requested_ids:
            query = query.filter(CostCenters.id.in_(requested_ids))
        search = " ".join(str(rq.args.get("search") or "").split())
        if search:
            pattern = f"%{search}%"
            query = query.filter(or_(CostCenters.local.ilike(pattern), CostCenters.nome.ilike(pattern),
                                     Company.nome.ilike(pattern), cast(CostCenters.centro_id, String).ilike(pattern)))
        company_ids = [int(value) for value in str(rq.args.get("empresa_ids") or "").split(",") if value.isdigit()]
        if company_ids: query = query.filter(CostCenters.empresa_id.in_(company_ids))
        departments = [int(value) for value in str(rq.args.get("departamentos") or "").split(",") if value.isdigit()]
        if departments: query = query.filter(CostCenters.departamento.in_(departments))
        query = query.order_by(Company.nome, CostCenters.centro_id, CostCenters.local)
        if str(rq.args.get("paginado") or "").lower() in {"1", "true"}:
            page = max(rq.args.get("page", 1, type=int), 1)
            per_page = min(max(rq.args.get("per_page", 25, type=int), 1), 100)
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            return jsonify({"items": [self._serialize_center(item) for item in pagination.items],
                            "page": pagination.page, "per_page": pagination.per_page,
                            "total": pagination.total, "pages": pagination.pages}), 200
        limit = rq.args.get("limit", type=int)
        if limit is not None:
            query = query.limit(min(max(limit, 1), 50))
        return jsonify([self._serialize_center(item) for item in query.all()]), 200

    @safe_route
    def create(self, token_data):
        if not is_admin(token_data): return jsonify("Apenas administradores podem cadastrar centros de custo."), 403
        body = rq.get_json(silent=True) or {}
        name = " ".join(str(body.get("nome") or "").strip().split()).upper()
        try:
            number = int(body.get("numero")); company = self._company(body.get("empresa_id"))
            capacity = None if body.get("capacidade_pessoas") in (None, "") else int(body["capacidade_pessoas"])
        except LookupError as error: return jsonify(str(error)), 404
        except (TypeError, ValueError): return jsonify("Informe empresa, número e capacidade válidos."), 400
        if not name or number <= 0 or capacity is not None and capacity < 0:
            return jsonify("Informe nome, número positivo e capacidade válida."), 400
        if CostCenters.query.filter_by(empresa_id=company.id, centro_id=number).first():
            return jsonify("Já existe um centro com este número para a empresa selecionada."), 409
        center = CostCenters(empresa_id=company.id, centro_id=number, nome=name, local=name, capacidade_pessoas=capacity)
        db.session.add(center); db.session.commit(); socketio.emit("data_changed", {"channel": "centros_custo", "resource": "centros_custo", "action": "created"})
        return jsonify({"message": "Centro de custo cadastrado com sucesso.", "centro": self._serialize_center(center)}), 201

    @safe_route
    def update(self, token_data):
        if not is_admin(token_data): return jsonify("Apenas administradores podem editar centros de custo."), 403
        body = rq.get_json(silent=True) or {}; center_id = body.get("id") or rq.args.get("id")
        try: center = db.session.get(CostCenters, int(center_id))
        except (TypeError, ValueError): center = None
        if not center: return jsonify("Centro de custo não encontrado."), 404
        try:
            if "empresa_id" in body and int(body["empresa_id"]) != center.empresa_id:
                company = self._company(body["empresa_id"])
                duplicate = CostCenters.query.filter(CostCenters.empresa_id == company.id, CostCenters.centro_id == center.centro_id, CostCenters.id != center.id).first()
                if duplicate: return jsonify("Já existe este código na empresa selecionada."), 409
                center.empresa_id = company.id
            if "numero" in body:
                number = int(body["numero"])
                if number <= 0: raise ValueError
                duplicate = CostCenters.query.filter(CostCenters.empresa_id == center.empresa_id, CostCenters.centro_id == number, CostCenters.id != center.id).first()
                if duplicate: return jsonify("Já existe este código na empresa selecionada."), 409
                center.centro_id = number
            if "nome" in body:
                name = " ".join(str(body["nome"] or "").split()).upper()
                if not name: raise ValueError
                center.nome = center.local = name
            if "capacidade_pessoas" in body:
                capacity = None if body["capacidade_pessoas"] in (None, "") else int(body["capacidade_pessoas"])
                if capacity is not None and capacity < 0: raise ValueError
                center.capacidade_pessoas = capacity
            db.session.commit()
        except LookupError as error: db.session.rollback(); return jsonify(str(error)), 404
        except (TypeError, ValueError): db.session.rollback(); return jsonify("Confira os dados do centro de custo."), 400
        socketio.emit("data_changed", {"channel": "centros_custo", "resource": "centros_custo", "action": "updated"})
        return jsonify({"message": "Centro de custo atualizado.", "centro": self._serialize_center(center)}), 200

    @safe_route
    def delete(self, token_data):
        if not is_admin(token_data): return jsonify("Apenas administradores podem excluir centros de custo."), 403
        center_id = rq.args.get("id", type=int)
        center = db.session.get(CostCenters, center_id) if center_id else None
        if not center: return jsonify("Centro de custo não encontrado."), 404
        if Employees.query.filter_by(centro_id=center.id).first():
            return jsonify("Não é possível excluir um centro com colaboradores vinculados."), 409
        db.session.delete(center); db.session.commit(); socketio.emit("data_changed", {"channel": "centros_custo", "resource": "centros_custo", "action": "deleted"})
        return jsonify({"message": "Centro de custo excluído."}), 200

    @safe_route
    def import_centers(self, token_data):
        if not is_admin(token_data): return jsonify("Apenas administradores podem importar centros de custo."), 403
        uploaded = rq.files.get("file")
        if not uploaded or Path(uploaded.filename).suffix.lower() not in {".xls", ".xlsx"}:
            return jsonify("Envie a planilha de centros em .xls ou .xlsx."), 400
        if rq.content_length and rq.content_length > MAX_IMPORT_SIZE: return jsonify("O arquivo deve ter no máximo 100 MB."), 413
        try: company = self._company(rq.form.get("empresa_id"))
        except LookupError as error: return jsonify(str(error)), 404
        except ValueError as error: return jsonify(str(error)), 400
        suffix = Path(uploaded.filename).suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            temporary.write(uploaded.read()); path = Path(temporary.name)
        job_id = uuid4().hex; now = time()
        with _imports_lock:
            _imports[job_id] = {"id": job_id, "status": "queued", "phase": "preparando", "percentual": 0,
                                "empresa_id": company.id, "empresa_nome": company.nome, "user_id": token_data.get("id"),
                                "created_at": now, "updated_at": now}
        app = current_app._get_current_object()
        Thread(target=self._run_center_import, args=(app, job_id, path, company.id), daemon=True).start()
        return jsonify(_import_snapshot(job_id)), 202

    @safe_route
    def sync_from_data(self, token_data):
        """Sincroniza o catálogo enviado pelo importador automático, sem exclusões."""
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem sincronizar centros de custo."), 403
        body = rq.get_json(silent=True) or {}
        try:
            company = self._company(body.get("empresa_id"))
        except LookupError as error:
            return jsonify(str(error)), 404
        except (TypeError, ValueError) as error:
            return jsonify(str(error) or "Empresa inválida."), 400

        records = body.get("centros")
        if not isinstance(records, list) or not records:
            return jsonify("Envie 'centros' como uma lista não vazia."), 400
        if len(records) > 10000:
            return jsonify("Cada carga pode conter no máximo 10.000 centros de custo."), 400

        centers = {}
        try:
            for index, record in enumerate(records, start=1):
                if not isinstance(record, dict):
                    raise ValueError(f"Centro {index}: conteúdo inválido.")
                number = int(record.get("codigo", record.get("centro_id")))
                name = " ".join(str(record.get("nome") or "").split()).upper()
                if number <= 0 or not name:
                    raise ValueError(f"Centro {index}: código e nome são obrigatórios.")
                previous = centers.get(number)
                if previous and previous != name:
                    raise ValueError(
                        f"Centro {number}: nomes divergentes na mesma carga "
                        f"('{previous}' e '{name}')."
                    )
                centers[number] = name
        except (TypeError, ValueError) as error:
            return jsonify(str(error) or "Existem centros inválidos na carga."), 400

        created = updated = ignored = 0
        with db.engine.begin() as connection:
            existing = {
                row["centro_id"]: dict(row)
                for row in connection.execute(
                    text(
                        "SELECT id, centro_id, nome, local FROM centro_de_custo "
                        "WHERE empresa_id = :company AND centro_id = ANY(:codes)"
                    ),
                    {"company": company.id, "codes": sorted(centers)},
                ).mappings()
            }
            for number, name in centers.items():
                current = existing.get(number)
                if current is None:
                    connection.execute(
                        text(
                            "INSERT INTO centro_de_custo "
                            "(empresa_id, centro_id, nome, local) "
                            "VALUES (:empresa_id, :centro_id, :nome, :local)"
                        ),
                        {"empresa_id": company.id, "centro_id": number, "nome": name, "local": name},
                    )
                    created += 1
                elif current["nome"] != name or current["local"] != name:
                    connection.execute(
                        text(
                            "UPDATE centro_de_custo SET nome = :nome, local = :local "
                            "WHERE id = :id"
                        ),
                        {"id": current["id"], "nome": name, "local": name},
                    )
                    updated += 1
                else:
                    ignored += 1

        if created or updated:
            socketio.emit("data_changed", {
                "channel": "centros_custo",
                "resource": "centros_custo",
                "action": "script_sync_completed",
            })
        current_app.logger.info(
            "Sincronização automática de centros: empresa=%s total=%s criados=%s atualizados=%s ignorados=%s",
            company.id, len(centers), created, updated, ignored,
        )
        return jsonify({
            "empresa_id": company.id,
            "total": len(centers),
            "centros_criados": created,
            "centros_atualizados": updated,
            "centros_ignorados": ignored,
        }), 200

    @staticmethod
    def _run_center_import(app, job_id, path: Path, company_id: int):
        with app.app_context():
            try:
                _update_import(job_id, status="processing", phase="lendo")
                parsed = parse_cost_center_spreadsheet(path)
                centers = parsed["centers"]
                if not centers: raise ValueError("A planilha não contém centros de custo válidos.")
                _update_import(job_id, phase="sincronizando", total=len(centers))
                created = updated = ignored = 0
                with db.engine.begin() as connection:
                    existing = {row["centro_id"]: dict(row) for row in connection.execute(text("SELECT id, centro_id, nome, local FROM centro_de_custo WHERE empresa_id = :company"), {"company": company_id}).mappings()}
                    for index, item in enumerate(centers, start=1):
                        row = existing.get(item["centro_id"])
                        if not row:
                            connection.execute(text("INSERT INTO centro_de_custo (empresa_id, centro_id, nome, local) VALUES (:empresa_id, :centro_id, :nome, :local)"), {"empresa_id": company_id, **item}); created += 1
                        elif row["nome"] != item["nome"] or row["local"] != item["local"]:
                            connection.execute(text("UPDATE centro_de_custo SET nome = :nome, local = :local WHERE id = :id"), {"id": row["id"], **item}); updated += 1
                        else: ignored += 1
                        if index % 25 == 0 or index == len(centers): _update_import(job_id, processados=index, percentual=round(index / len(centers) * 100, 2))
                _update_import(job_id, status="completed", phase="concluido", percentual=100, processados=len(centers), total=len(centers), centros_criados=created, centros_atualizados=updated, centros_ignorados=ignored, registros_invalidos=len(parsed["invalid"]), duplicidades=parsed["duplicates"], erros=parsed["invalid"][:20])
                socketio.emit("data_changed", {"channel": "centros_custo", "resource": "centros_custo", "action": "import_completed"})
            except Exception as error:
                _update_import(job_id, status="error", phase="erro", erro=str(error))
            finally:
                path.unlink(missing_ok=True)

    @safe_route
    def import_status(self, job_id, token_data):
        if not is_admin(token_data): return jsonify("Apenas administradores podem acompanhar importações."), 403
        job = _import_snapshot(job_id)
        return (jsonify(job), 200) if job else (jsonify("Importação não encontrada."), 404)

    @staticmethod
    def _settings_payload():
        centers = CostCenters.query.order_by(CostCenters.departamento, CostCenters.local).all()
        configured = {item.departamento: item for item in DepartmentConfiguration.query.all()}
        departments = sorted({*(item.departamento for item in centers if item.departamento is not None), *configured.keys()})
        counts = dict(db.session.query(CostCenters.departamento, db.func.count(Employees.id)).outerjoin(Employees, Employees.centro_id == CostCenters.id).filter(CostCenters.departamento.isnot(None), Employees.situacao == 1).group_by(CostCenters.departamento).all())
        return {"departamentos": [{"departamento": item, "ativo": configured.get(item).ativo if item in configured else True, "capacidade_pessoas": configured.get(item).capacidade_pessoas if item in configured else None, "colaboradores_cadastrados": counts.get(item, 0)} for item in departments]}

    @safe_route
    def settings(self, token_data):
        if not is_admin(token_data): return jsonify("Apenas administradores podem configurar departamentos."), 403
        return jsonify(self._settings_payload()), 200

    @safe_route
    def update_settings(self, token_data):
        if not is_admin(token_data): return jsonify("Apenas administradores podem configurar departamentos."), 403
        body = rq.get_json(silent=True) or {}; capacities = body.get("capacidades_departamentos") or []; departments = body.get("departamentos") or []
        if not isinstance(capacities, list) or not isinstance(departments, list): return jsonify("Formato de configuração inválido."), 400
        try:
            valid = {value for value, in db.session.query(CostCenters.departamento).filter(CostCenters.departamento.isnot(None)).distinct()}; valid.update(value for value, in db.session.query(DepartmentConfiguration.departamento))
            changed = {}
            for item in capacities:
                department = int(item["departamento"])
                if department not in valid: return jsonify("Departamento não encontrado."), 404
                value = None if item.get("capacidade_pessoas") in (None, "") else int(item["capacidade_pessoas"])
                if value is not None and value < 0: raise ValueError
                config = db.session.get(DepartmentConfiguration, department) or DepartmentConfiguration(departamento=department); db.session.add(config); config.capacidade_pessoas = value; changed[department] = config
            for item in departments:
                department = int(item["departamento"])
                if department not in valid: return jsonify("Departamento não encontrado."), 404
                config = db.session.get(DepartmentConfiguration, department) or DepartmentConfiguration(departamento=department); db.session.add(config); config.ativo = bool(item.get("ativo", True)); changed[department] = config
            db.session.commit()
        except (KeyError, TypeError, ValueError): db.session.rollback(); return jsonify("Informe dados de departamento válidos."), 400
        socketio.emit("ql_update", {"action": "planning_updated"})
        return jsonify({"departamentos": [{"departamento": item.departamento, "ativo": item.ativo, "capacidade_pessoas": item.capacidade_pessoas} for item in changed.values()]}), 200
