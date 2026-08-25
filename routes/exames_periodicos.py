# Rotas HTTP do controle de exames periódicos.
# Dependências externas.
from flask import Blueprint

# Módulos internos da aplicação.
from services.exames_periodicos import PeriodicExamService


periodic_exams_bp = Blueprint("Exames Periodicos", __name__)
service = PeriodicExamService()


@periodic_exams_bp.get("")
def read():
    return service.read()


@periodic_exams_bp.post("/importar")
def import_spreadsheet():
    return service.import_spreadsheet()


@periodic_exams_bp.get("/exportar")
def export_spreadsheet():
    return service.export_spreadsheet()


@periodic_exams_bp.patch("/lote/status")
def update_bulk_status():
    return service.update_bulk_status()


@periodic_exams_bp.patch("/<int:exam_id>")
def update(exam_id):
    return service.update(exam_id)


@periodic_exams_bp.delete("/todos")
def delete_all():
    return service.delete_all()
