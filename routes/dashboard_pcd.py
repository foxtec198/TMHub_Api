from flask import Blueprint

from services.dashboard_pcd import PcdDashboardService


dashboard_pcd_bp = Blueprint("PcdDashboard", __name__)
service = PcdDashboardService()


@dashboard_pcd_bp.get("")
def root():
    return service.read()
