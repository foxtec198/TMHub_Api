# Rotas HTTP do dashboard de período de experiência.
from flask import Blueprint

from services.dashboard_experiencias import ExperienceDashboardService


experience_dashboard_bp = Blueprint("Dashboard de Experiência", __name__)
service = ExperienceDashboardService()


@experience_dashboard_bp.get("")
def read():
    """Entrega o resumo executivo das avaliações de período de experiência."""
    return service.read()
