from flask import Blueprint

from services.medidas_disciplinares import DisciplinaryMeasureService


disciplinary_measures_bp = Blueprint("Controle de Medidas Disciplinares", __name__)
service = DisciplinaryMeasureService()


@disciplinary_measures_bp.get("")
def root():
    return service.read()


@disciplinary_measures_bp.get("/opcoes-filtros")
def filter_options():
    return service.filter_options()


@disciplinary_measures_bp.delete("/todos")
def delete_all():
    return service.delete_all()


@disciplinary_measures_bp.post("/importar")
def import_xlsx():
    return service.import_xlsx()
