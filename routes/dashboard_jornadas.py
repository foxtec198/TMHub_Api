"""Rota HTTP do dashboard de Jornadas."""
from flask import Blueprint

from services.dashboard_jornadas import JourneyDashboardService


journey_dashboard_bp = Blueprint("Dashboard de Jornadas", __name__)
service = JourneyDashboardService()


@journey_dashboard_bp.get("")
def read():
    return service.read()
