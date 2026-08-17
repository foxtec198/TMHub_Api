# Rotas HTTP de dashboard PCD.
# Dependências externas.
from flask import Blueprint

# Módulos internos da aplicação.
from services.dashboard_pcd import PcdDashboardService


dashboard_pcd_bp = Blueprint("PcdDashboard", __name__)
service = PcdDashboardService()


# Encaminha a requisição para o fluxo principal do módulo.
@dashboard_pcd_bp.get("")
def root():
    return service.read()
