from flask import request, Blueprint
from services.dashboard import DashboardService

dashboards_bp = Blueprint("Dashboards", __name__)
service = DashboardService()

@dashboards_bp.route("/reposicoes", methods=["POST"])
def root(): return service.get_repos()

@dashboards_bp.route("/colaboradores-departamento", methods=["POST"])
def employees_by_department(): return service.get_employees_by_department()
