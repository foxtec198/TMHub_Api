from flask import request as rq, jsonify
from utils.safe_route import safe_route
from models.centros_de_custo import CostCenters, DepartmentConfiguration
from models.colaboradores import Employees
from utils.db import db
from utils.filial_scope import apply_cost_center_scope, can_access_cost_center, is_admin

class CostsCenterService():
    @staticmethod
    def _settings_payload():
        centers = CostCenters.query.order_by(
            CostCenters.departamento,
            CostCenters.local,
        ).all()
        department_numbers = sorted({
            center.departamento for center in centers if center.departamento is not None
        })
        configured = {
            item.departamento: item
            for item in DepartmentConfiguration.query.filter(
                DepartmentConfiguration.departamento.in_(department_numbers)
            ).all()
        } if department_numbers else {}

        employee_counts = {
            center_id: total
            for center_id, total in (
                db.session.query(Employees.centro_id, db.func.count(Employees.id))
                .filter(Employees.centro_id.isnot(None))
                .group_by(Employees.centro_id)
                .all()
            )
        }

        return {
            "centros_custo": [
                {
                    "id": center.id,
                    "local": center.local,
                    "departamento": center.departamento,
                    "capacidade_pessoas": center.capacidade_pessoas,
                    "colaboradores_cadastrados": employee_counts.get(center.id, 0),
                }
                for center in centers
            ],
            "departamentos": [
                {
                    "departamento": department,
                    "ativo": configured.get(department).ativo if department in configured else True,
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
        capacities = body.get("capacidades") or []
        departments = body.get("departamentos") or []
        if not isinstance(capacities, list) or not isinstance(departments, list):
            return jsonify("Formato de configuração inválido."), 400

        changed_centers = []
        changed_departments = []
        try:
            for item in capacities:
                if not isinstance(item, dict):
                    raise ValueError
                center_id = int(item.get("centro_custo_id"))
                capacity = item.get("capacidade_pessoas")
                if capacity in (None, ""):
                    normalized_capacity = None
                else:
                    normalized_capacity = int(capacity)
                    if normalized_capacity < 0:
                        raise ValueError
                center = db.session.get(CostCenters, center_id)
                if not center:
                    return jsonify("Centro de custo não encontrado."), 404
                center.capacidade_pessoas = normalized_capacity
                changed_centers.append(center)

            valid_departments = {
                value for value, in db.session.query(CostCenters.departamento)
                .filter(CostCenters.departamento.isnot(None))
                .distinct()
                .all()
            }
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
                changed_departments.append(configuration)
            db.session.commit()
        except (TypeError, ValueError):
            db.session.rollback()
            return jsonify("Informe capacidades inteiras iguais ou maiores que zero."), 400

        serialized_departments = [
            {
                "departamento": configuration.departamento,
                "ativo": configuration.ativo,
            }
            for configuration in changed_departments
        ]

        return jsonify({
            "centros_custo": [
                {
                    "id": center.id,
                    "capacidade_pessoas": center.capacidade_pessoas,
                }
                for center in changed_centers
            ],
            "departamentos": serialized_departments,
        }), 200
