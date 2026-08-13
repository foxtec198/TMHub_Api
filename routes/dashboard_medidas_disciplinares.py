from flask import Blueprint

from services.dashboard_medidas_disciplinares import (
    DisciplinaryMeasuresDashboardService,
)


disciplinary_measures_dashboard_bp = Blueprint(
    "Dashboard de Medidas Disciplinares",
    __name__,
)
service = DisciplinaryMeasuresDashboardService()


@disciplinary_measures_dashboard_bp.get("")
def read():
    return service.read()
