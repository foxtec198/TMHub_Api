from flask import Blueprint, request as rq
from services.reposicao import ReplaceService, RequestService

replace_bp = Blueprint("Reposições", __name__)

service = ReplaceService()
rq_service = RequestService()

# Salva o historico das requisições
@replace_bp.route("", methods=["POST"])
def root(): return service.create()

# Obtem o historico salvo
@replace_bp.route("/history", methods=["POST"])
def get_history(): return service.read()

# Requisições
@replace_bp.route("/request", methods=["GET", "POST"])
def request():
    match rq.method:
        case "GET": response = rq_service.read()
        case "POST": response = rq_service.create()
    return response
    