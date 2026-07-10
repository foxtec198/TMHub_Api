from services.reposicoes import HistoryService, RequestService, TimelineService
from flask import Blueprint, request as rq

replace_bp = Blueprint("Reposições", __name__)

history_service = HistoryService()
rq_service = RequestService()
timeline_service = TimelineService()

# Salva o historico das requisições
@replace_bp.route("", methods=["POST"])
def root(): return history_service.create()

# Historico
@replace_bp.route("/history", methods=["POST", "PATCH", "DELETE"])
def history():
    match rq.method:
        case "POST": return history_service.read()
        case "PATCH": return history_service.update()
        case "DELETE": return history_service.delete()

# Requisições
@replace_bp.route("/request", methods=["GET", "POST", "PATCH", "DELETE"])
def request():
    match rq.method:
        case "GET": return rq_service.read()
        case "POST": return rq_service.create()
        case "PATCH": return rq_service.update()
        case "DELETE": return rq_service.delete()

# Timeline de eventos
@replace_bp.route("/timeline", methods=["GET"])
def timeline(): return timeline_service.read()
