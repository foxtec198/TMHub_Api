from flask import Blueprint

from services.dashboard_reservas import ReservationDashboardService


dashboard_reservas_bp = Blueprint("ReservationDashboard", __name__)
service = ReservationDashboardService()


@dashboard_reservas_bp.get("")
def root():
    return service.read()
