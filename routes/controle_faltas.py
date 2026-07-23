from flask import Blueprint, request

from services.controle_faltas import AbsenceControlService


absence_control_bp = Blueprint("Controle de Faltas", __name__)
service = AbsenceControlService()


@absence_control_bp.route("", methods=["GET", "PATCH"])
def root():
    return service.read() if request.method == "GET" else service.update()


@absence_control_bp.get("/dashboard")
def dashboard():
    return service.dashboard()
