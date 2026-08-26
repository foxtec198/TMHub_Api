# Dependências externas.
from flask import Blueprint

# Módulos internos da aplicação.
from services.ferias import VacationService


vacation_bp = Blueprint("Controle de Férias", __name__)
service = VacationService()


@vacation_bp.get("")
def read():
    return service.read()


@vacation_bp.post("/importar")
def import_xlsx():
    return service.import_xlsx()


@vacation_bp.post("/importar/previa")
def preview_import():
    return service.preview_import()


@vacation_bp.get("/export")
def export_xlsx():
    return service.export_xlsx()


@vacation_bp.patch("/<int:period_id>")
def update_period(period_id):
    return service.update_period(period_id)


@vacation_bp.post("/<int:period_id>/gozos")
def create_leave(period_id):
    return service.create_leave(period_id)


@vacation_bp.patch("/gozos/<int:leave_id>")
def update_leave(leave_id):
    return service.update_leave(leave_id)


@vacation_bp.delete("/gozos/<int:leave_id>")
def delete_leave(leave_id):
    return service.delete_leave(leave_id)


@vacation_bp.post("/concluir")
def complete_periods():
    return service.complete_periods()


@vacation_bp.delete("/todos")
def delete_all():
    return service.delete_all()
