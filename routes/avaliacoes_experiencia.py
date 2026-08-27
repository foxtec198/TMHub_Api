# Rotas HTTP do controle de período de experiência.
from flask import Blueprint, request

from services.avaliacoes_experiencia import ExperienceEvaluationService


experience_evaluations_bp = Blueprint("Avaliações de Experiência", __name__)
service = ExperienceEvaluationService()


# Tela do supervisor: consulta somente tarefas abertas da sessão autenticada.
@experience_evaluations_bp.get("/supervisores")
def supervisors():
    return service.supervisors()


@experience_evaluations_bp.get("/tarefas-supervisor")
def supervisor_tasks():
    return service.supervisor_tasks()


# Tela de gestão de RH: visão de todos em experiência e fila de avaliações.
@experience_evaluations_bp.get("/em-experiencia")
def active_employees():
    return service.active_employees()


@experience_evaluations_bp.get("/assinaturas-cadastradas")
def registered_signatures():
    return service.registered_signatures()


@experience_evaluations_bp.route("", methods=["GET", "POST"])
def root():
    return service.read_rh() if request.method == "GET" else service.process()


@experience_evaluations_bp.get("/<int:evaluation_id>")
def detail(evaluation_id):
    return service.detail(evaluation_id)


@experience_evaluations_bp.patch("/<int:evaluation_id>/supervisor")
def update_supervisor(evaluation_id):
    return service.update_supervisor(evaluation_id)


@experience_evaluations_bp.post("/<int:evaluation_id>/supervisor/concluir")
def complete_supervisor(evaluation_id):
    return service.complete_supervisor(evaluation_id)


@experience_evaluations_bp.post("/<int:evaluation_id>/supervisor/assinatura")
def supervisor_signature(evaluation_id):
    return service.upload_supervisor_signature(evaluation_id)


@experience_evaluations_bp.patch("/<int:evaluation_id>/rh")
def update_rh(evaluation_id):
    return service.update_rh(evaluation_id)


@experience_evaluations_bp.post("/<int:evaluation_id>/rh/concluir")
def complete_rh(evaluation_id):
    return service.complete_rh(evaluation_id)


@experience_evaluations_bp.post("/<int:evaluation_id>/rh/assinatura")
def rh_signature(evaluation_id):
    return service.upload_rh_signature(evaluation_id)


@experience_evaluations_bp.post("/<int:evaluation_id>/rh/assinatura-cadastrada")
def registered_rh_signature(evaluation_id):
    return service.use_registered_rh_signature(evaluation_id)


@experience_evaluations_bp.post("/<int:evaluation_id>/cancelar")
def cancel(evaluation_id):
    return service.cancel(evaluation_id)


@experience_evaluations_bp.delete("/<int:evaluation_id>")
def delete(evaluation_id):
    return service.delete(evaluation_id)


@experience_evaluations_bp.patch("/<int:evaluation_id>/estado")
def update_status(evaluation_id):
    return service.update_status(evaluation_id)


@experience_evaluations_bp.get("/<int:evaluation_id>/export")
def export_pdf(evaluation_id):
    return service.export_pdf(evaluation_id)
