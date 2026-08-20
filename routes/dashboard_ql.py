from flask import Blueprint

from services.dashboard_ql import QLDashboardService


dashboard_ql_bp = Blueprint("QLDashboard", __name__)
service = QLDashboardService()


@dashboard_ql_bp.get("")
def root():
    return service.read()

@dashboard_ql_bp.get("/diario")
def diario():
    return service.read_diario()
