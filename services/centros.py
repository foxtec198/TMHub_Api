# Regras de negócio de centros de custo.
# Dependências externas.
from flask import request as rq, jsonify
# Módulos internos da aplicação.
from utils.safe_route import safe_route
from models.centros_de_custo import CostCenters, DepartmentConfiguration
from models.colaboradores import Employees
from utils.db import db
from utils.filial_scope import apply_cost_center_scope, can_access_cost_center, is_admin
from utils.socket import socketio

class CostsCenterService():
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
            if not can_access_cost_center(token_data, int(id)):
                return jsonify("Você não possui acesso à filial deste centro de custo"), 403
            cost = CostCenters().query.filter_by(id=id).first()
            return jsonify(cost), 200 if cost else jsonify("Centro de custo não encontrado"), 404
        
        costs_query = CostCenters.query
        costs_query = apply_cost_center_scope(
            costs_query, CostCenters.id, token_data
        )
        costs = costs_query.all()
        return jsonify([c.to_dict() for c in costs])

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
