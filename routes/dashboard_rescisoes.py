# Rotas HTTP de dashboard de rescisões.
# Dependências externas.
from flask import Blueprint

# Módulos internos da aplicação.
from services.dashboard_rescisoes import TerminationDashboardService


termination_dashboard_bp = Blueprint("Dashboard de Rescisoes", __name__)
service = TerminationDashboardService()


@termination_dashboard_bp.get("")
def read():
    return service.read()
