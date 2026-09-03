from flask import Blueprint

from services.jornadas import JourneyControlService


journey_bp = Blueprint("Jornadas", __name__)
service = JourneyControlService()


@journey_bp.get("")
def read():
    return service.read()


@journey_bp.post("/importar")
def import_spreadsheet():
    return service.import_spreadsheet()


@journey_bp.post("/automatizar")
def automate_import():
    return service.automate_import()


@journey_bp.get("/opcoes-filtros")
def filter_options():
    return service.filter_options()


@journey_bp.patch("/<int:record_id>")
def update_record(record_id):
    return service.update_record(record_id)


@journey_bp.get("/exportar")
def export_spreadsheet():
    return service.export_spreadsheet()
