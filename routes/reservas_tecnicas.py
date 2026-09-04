# Rotas HTTP de reservas técnicas.
# Dependências externas.
from flask import request, Blueprint, jsonify
# Módulos internos da aplicação.
from services.reservas_tecnicas import FloaterService
from models.colaboradores import Employees
from models.centros_de_custo import CostCenters
from models.reservas_tecnicas import Floaters
from utils.db import db

floaters_bp = Blueprint("Reservas Tecnicas", __name__)
service = FloaterService()

# Encaminha a requisição para o fluxo principal do módulo.
@floaters_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def root():
    match request.method:
        case "GET": return service.read()
        case "POST": return service.add()
        case "PATCH": return service.update()
        case "DELETE": return service.remove()

@floaters_bp.get("/opcoes-filtros")
def floater_filter_options():
    """Retorna as opções de filtros para departamentos e centros de custo baseados nas reservas ativas."""
    # Obter centros de custo que têm pelo menos uma reserva ativa
    cost_center_options = db.session.query(
        CostCenters.id.label("value"),
        CostCenters.local.label("label"),
        CostCenters.departamento.label("departamento")
    ).filter(
        CostCenters.id.in_(
            db.session.query(Employees.centro_id).filter(
                Employees.id.in_(db.session.query(Floaters.employee_id))
            )
        )
    ).order_by(CostCenters.departamento, CostCenters.local).all()
    
    # Agrupar departamentos únicos
    department_options = []
    seen_departments = set()
    for row in cost_center_options:
        if row.departamento not in seen_departments:
            department_options.append({"value": row.departamento, "label": f"DPTO. {row.departamento}"})
            seen_departments.add(row.departamento)
    
    return jsonify({
        "departamentos": department_options,
        "centros": [{"value": row.value, "label": row.label} for row in cost_center_options]
    })
