# Regras de negócio de centros de custo.
# Dependências externas.
from flask import request as rq, jsonify
# Módulos internos da aplicação.
from utils.safe_route import safe_route
from models.centros_de_custo import CostCenters, DepartmentConfiguration
from models.empresas import Company
from models.colaboradores import Employees
from utils.db import db
from utils.filial_scope import apply_cost_center_scope, can_access_cost_center, is_admin
from utils.socket import socketio

class CostsCenterService():
    @staticmethod
    def _serialize_center(center):
        return {
            "id": center.id,
            "numero": center.centro_id,
            "nome": center.nome,
            "local": center.local,
            "departamento": center.departamento,
            "capacidade_pessoas": center.capacidade_pessoas,
            "empresa_id": center.empresa_id,
            "empresa_nome": center.empresa.nome if center.empresa else None,
        }

    @safe_route
    def companies(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem consultar empresas."), 403
        return jsonify([
            {"id": company.id, "nome": company.nome, "ativa": bool(company.ativa)}
            for company in Company.query.order_by(Company.ativa.desc(), Company.nome).all()
        ])

    @staticmethod
    def _settings_payload():
        centers = CostCenters.query.order_by(
            CostCenters.departamento,
            CostCenters.local,
        ).all()
        configured = {
            item.departamento: item
            for item in DepartmentConfiguration.query.all()
        }
        department_numbers = sorted({
            *(center.departamento for center in centers if center.departamento is not None),
            *configured.keys(),
        })

        department_counts = {
            department: total
            for department, total in (
                db.session.query(CostCenters.departamento, db.func.count(Employees.id))
                .outerjoin(Employees, Employees.centro_id == CostCenters.id)
                .filter(CostCenters.departamento.isnot(None), Employees.situacao == 1)
                .group_by(CostCenters.departamento)
                .all()
            )
        }

        return {
            "departamentos": [
                {
                    "departamento": department,
                    "ativo": configured.get(department).ativo if department in configured else True,
                    "capacidade_pessoas": configured.get(department).capacidade_pessoas if department in configured else None,
                    "colaboradores_cadastrados": department_counts.get(department, 0),
                }
                for department in department_numbers
            ],
        }

    @safe_route
    def read(self, token_data):
        id = rq.args.get("id")

        if id:
            try:
                center_id = int(id)
            except (TypeError, ValueError):
                return jsonify("Identificador de centro de custo inválido."), 400
            if not can_access_cost_center(token_data, center_id):
                return jsonify("Você não possui acesso à filial deste centro de custo"), 403
            cost = db.session.get(CostCenters, center_id)
            if not cost:
                return jsonify("Centro de custo não encontrado."), 404
            return jsonify(self._serialize_center(cost)), 200
        
        costs_query = CostCenters.query
        costs_query = apply_cost_center_scope(
            costs_query, CostCenters.id, token_data
        )
        costs = costs_query.all()
        return jsonify([self._serialize_center(cost) for cost in costs])

    @safe_route
    def create(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem cadastrar centros de custo."), 403

        body = rq.get_json(silent=True) or {}
        name = " ".join(str(body.get("nome") or "").strip().split()).upper()
        try:
            number = int(body.get("numero"))
            company_id = int(body.get("empresa_id"))
        except (TypeError, ValueError):
            return jsonify("Informe o número e a empresa do centro de custo."), 400
        if not name:
            return jsonify("Informe o nome do centro de custo."), 400
        if number <= 0:
            return jsonify("O número do centro de custo deve ser maior que zero."), 400
        capacity = body.get("capacidade_pessoas")
        try:
            capacity = None if capacity in (None, "") else int(capacity)
        except (TypeError, ValueError):
            return jsonify("A capacidade deve ser um número inteiro igual ou maior que zero."), 400
        if capacity is not None and capacity < 0:
            return jsonify("A capacidade deve ser um número inteiro igual ou maior que zero."), 400

        company = db.session.get(Company, company_id)
        if not company:
            return jsonify("Empresa não encontrada."), 404
        if not company.ativa:
            return jsonify("A empresa selecionada está inativa."), 409
        if CostCenters.query.filter_by(empresa_id=company.id, centro_id=number).first():
            return jsonify("Já existe um centro com este número para a empresa selecionada."), 409

        center = CostCenters(
            empresa_id=company.id,
            centro_id=number,
            nome=name,
            local=name,
            capacidade_pessoas=capacity,
        )
        db.session.add(center)
        db.session.commit()
        return jsonify({
            "message": "Centro de custo cadastrado com sucesso.",
            "centro": self._serialize_center(center),
        }), 201

    @safe_route
    def settings(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem configurar departamentos e contratos."), 403

        return jsonify(self._settings_payload()), 200

    @safe_route
    def update_settings(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem configurar departamentos e contratos."), 403

        body = rq.get_json(silent=True) or {}
        department_capacities = body.get("capacidades_departamentos") or []
        departments = body.get("departamentos") or []
        if not isinstance(department_capacities, list) or not isinstance(departments, list):
            return jsonify("Formato de configuração inválido."), 400

        changed_departments = []
        try:
            valid_departments = {
                value for value, in db.session.query(CostCenters.departamento)
                .filter(CostCenters.departamento.isnot(None))
                .distinct()
                .all()
            }
            valid_departments.update(
                value for value, in db.session.query(DepartmentConfiguration.departamento).all()
            )
            changed_by_department = {}
            for item in department_capacities:
                if not isinstance(item, dict):
                    raise ValueError
                department = int(item.get("departamento"))
                if department not in valid_departments:
                    return jsonify("Departamento não encontrado."), 404
                capacity = item.get("capacidade_pessoas")
                if capacity in (None, ""):
                    normalized_capacity = None
                else:
                    normalized_capacity = int(capacity)
                    if normalized_capacity < 0:
                        raise ValueError
                configuration = db.session.get(DepartmentConfiguration, department)
                if not configuration:
                    configuration = DepartmentConfiguration(departamento=department)
                    db.session.add(configuration)
                configuration.capacidade_pessoas = normalized_capacity
                changed_by_department[department] = configuration

            for item in departments:
                if not isinstance(item, dict):
                    raise ValueError
                department = int(item.get("departamento"))
                if department not in valid_departments:
                    return jsonify("Departamento não encontrado."), 404
                configuration = db.session.get(DepartmentConfiguration, department)
                if not configuration:
                    configuration = DepartmentConfiguration(departamento=department)
                    db.session.add(configuration)
                configuration.ativo = bool(item.get("ativo", True))
                changed_by_department[department] = configuration
            changed_departments = list(changed_by_department.values())
            db.session.commit()
        except (TypeError, ValueError):
            db.session.rollback()
            return jsonify("Informe capacidades inteiras iguais ou maiores que zero."), 400

        serialized_departments = [
            {
                "departamento": configuration.departamento,
                "ativo": configuration.ativo,
                "capacidade_pessoas": configuration.capacidade_pessoas,
            }
            for configuration in changed_departments
        ]

        if changed_departments:
            socketio.emit("ql_update", {"action": "planning_updated"})

        return jsonify({
            "departamentos": serialized_departments,
        }), 200
