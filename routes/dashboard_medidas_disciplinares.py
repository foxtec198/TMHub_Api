# Rotas HTTP de dashboard de medidas disciplinares.
# Dependências externas.
from flask import Blueprint

# Módulos internos da aplicação.
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
