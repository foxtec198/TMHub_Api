from services.reposicoes import HistoryService, RequestService, TimelineService
from flask import Blueprint, request as rq

replace_bp = Blueprint("Reposições", __name__)

history_service = HistoryService()
rq_service = RequestService()
timeline_service = TimelineService()

# Salva o historico das requisições
@replace_bp.route("", methods=["POST"])
def root(): return history_service.create()

# Obtem o historico salvo
@replace_bp.route("/history", methods=["POST"])
def get_history(): return history_service.read()

# Requisições
@replace_bp.route("/request", methods=["GET", "POST", "PATCH"])
def request():
    match rq.method:
        case "GET": return rq_service.read()
        case "POST": return rq_service.create()
        case "PATCH": return rq_service.update()

# Timeline de eventos
@replace_bp.route("/timeline", methods=["GET"])
def timeline(): return timeline_service.read()

# Alterar requisição aberta
@replace_bp.route("/request/<int:id>", methods=["PATCH"])
def update_request(id): return rq_service.update(id)