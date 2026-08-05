from flask import jsonify, request
from models.centros_de_custo import CostCenters
from models.filiais import Branch, filial_departamentos
from models.usuarios import Users
from utils.db import db
from utils.filial_scope import is_admin, is_matrix_user
from utils.safe_route import safe_route
from sqlalchemy.orm import selectinload

class BranchService:
    @staticmethod
    def _serialize(branch, detailed=False, departments=None):
        payload = {"id": branch.id, "nome": branch.nome, "ativa": branch.ativa}
        if detailed:
            payload.update(
                {
                    "usuario_ids": sorted(user.id for user in branch.usuarios),
                    "centro_custo_ids": sorted(
                        center.id for center in branch.centros_custo
                    ),
                    "departamentos": sorted(
                        departments.get(branch.id, []) if departments is not None else (
                            row[0]
                            for row in db.session.query(filial_departamentos.c.departamento)
                            .filter(filial_departamentos.c.filial_id == branch.id)
                            .all()
                        )
                    ),
                }
            )
        return payload

    @safe_route
    def read(self, token_data):
        if is_admin(token_data) or is_matrix_user(token_data):
            branches = (
                Branch.query.options(
                    selectinload(Branch.usuarios),
                    selectinload(Branch.centros_custo),
                ).filter(Branch.ativa.is_(True)).order_by(Branch.nome).all()
            )
            department_map = {branch.id: [] for branch in branches}
            branch_ids = list(department_map)
            if branch_ids:
                for branch_id, department in db.session.query(
                    filial_departamentos.c.filial_id,
                    filial_departamentos.c.departamento,
                ).filter(filial_departamentos.c.filial_id.in_(branch_ids)).all():
                    department_map[branch_id].append(department)
            return jsonify([
                self._serialize(item, True, department_map) for item in branches
            ]), 200

        user = db.session.get(Users, token_data.get("id"))
        branches = sorted(
            (branch for branch in (user.filiais if user else []) if branch.ativa),
            key=lambda item: item.nome,
        )
        return jsonify([self._serialize(item) for item in branches]), 200

    @safe_route
    def create(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem criar filiais."), 403
        body = request.get_json(silent=True) or {}
        name = str(body.get("nome") or "").strip()
        if len(name) < 2:
            return jsonify("Informe o nome da filial."), 400
        if Branch.query.filter(db.func.lower(Branch.nome) == name.lower()).first():
            return jsonify("Já existe uma filial com este nome."), 409
        branch = Branch(nome=name, ativa=bool(body.get("ativa", True)))
        db.session.add(branch)
        db.session.flush()
        error = self._apply_links(branch, body)
        if error:
            db.session.rollback()
            return jsonify(error), 400
        db.session.commit()
        return jsonify(self._serialize(branch, True)), 201

    @safe_route
    def update(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem alterar filiais."), 403
        body = request.get_json(silent=True) or {}
        branch = db.session.get(Branch, body.get("id"))
        if not branch:
            return jsonify("Filial não encontrada."), 404
        if "nome" in body:
            name = str(body.get("nome") or "").strip()
            duplicate = Branch.query.filter(
                db.func.lower(Branch.nome) == name.lower(), Branch.id != branch.id
            ).first()
            if len(name) < 2 or duplicate:
                return jsonify("Informe um nome válido e não repetido."), 400
            branch.nome = name
        if "ativa" in body:
            branch.ativa = bool(body.get("ativa"))
        error = self._apply_links(branch, body)
        if error:
            return jsonify(error), 400
        db.session.commit()
        return jsonify(self._serialize(branch, True)), 200

    @staticmethod
    def _apply_links(branch, body):
        if "usuario_ids" in body:
            ids = {int(value) for value in (body.get("usuario_ids") or [])}
            users = Users.query.filter(Users.id.in_(ids)).all() if ids else []
            if len(users) != len(ids):
                return "Um ou mais usuários não foram encontrados."
            branch.usuarios = users
        if "centro_custo_ids" in body:
            ids = {int(value) for value in (body.get("centro_custo_ids") or [])}
            centers = (
                CostCenters.query.filter(CostCenters.id.in_(ids)).all() if ids else []
            )
            if len(centers) != len(ids):
                return "Um ou mais contratos não foram encontrados."
            branch.centros_custo = centers
        if "departamentos" in body:
            try:
                departments = {
                    int(value) for value in (body.get("departamentos") or [])
                }
            except (TypeError, ValueError):
                return "Informe departamentos válidos."
            valid = (
                {
                    row[0]
                    for row in db.session.query(CostCenters.departamento)
                    .filter(CostCenters.departamento.in_(departments))
                    .distinct()
                    .all()
                }
                if departments
                else set()
            )
            if valid != departments:
                return "Um ou mais departamentos não foram encontrados."
            if branch.id:
                db.session.execute(
                    filial_departamentos.delete().where(
                        filial_departamentos.c.filial_id == branch.id
                    )
                )
            for department in departments:
                db.session.execute(
                    filial_departamentos.insert().values(
                        filial_id=branch.id, departamento=department
                    )
                )
        return None

    @safe_route
    def options(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem configurar filiais."), 403
        centers = db.session.query(
            CostCenters.id, CostCenters.local, CostCenters.departamento
        ).order_by(CostCenters.departamento, CostCenters.local).all()
        users = db.session.query(
            Users.id, Users.nome, Users.role
        ).order_by(Users.nome).all()
        return (
            jsonify(
                {
                    "centros_custo": [
                        {
                            "id": item.id,
                            "local": item.local,
                            "departamento": item.departamento,
                        }
                        for item in centers
                    ],
                    "usuarios": [
                        {"id": item.id, "nome": item.nome, "role": item.role}
                        for item in users
                    ],
                }
            ),
            200,
        )
