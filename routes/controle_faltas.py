# Rotas HTTP de controle de faltas.
# Dependências externas.
from flask import Blueprint, request
# Módulos internos da aplicação.
from services.controle_faltas import AbsenceControlService


absence_control_bp = Blueprint("Controle de Faltas", __name__)
service = AbsenceControlService()


# Encaminha a requisição para o fluxo principal do módulo.
@absence_control_bp.route("", methods=["GET", "POST", "PATCH"])
def root():
    if request.method == "GET": return service.read()
    if request.method == "POST": return service.create_manual()
    return service.update()


@absence_control_bp.get("/dashboard")
def dashboard(): return service.dashboard()

@absence_control_bp.get("/tt")
def tt(): return service.total()

@absence_control_bp.get("/export")
def export(): return service.export()