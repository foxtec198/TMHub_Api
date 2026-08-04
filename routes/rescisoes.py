from flask import Blueprint, request

from services.rescisoes import TerminationService


termination_bp = Blueprint("Controle de Rescisoes", __name__)
service = TerminationService()


@termination_bp.get("")
def read():
    return service.read()


@termination_bp.post("/importar")
def import_xlsx():
    return service.import_xlsx()


@termination_bp.post("/calcular")
def calculate():
    return service.calculate()


@termination_bp.delete("/todos")
def delete_all():
    return service.delete_all()


@termination_bp.delete("/<int:termination_id>")
def delete(termination_id):
    return service.delete(termination_id)
