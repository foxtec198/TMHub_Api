from flask import Blueprint, request as rq
from services.reposicao import ReplaceService, RequestService

replace_bp = Blueprint("Reposições", __name__)

service = ReplaceService()
rq_service = RequestService()

@replace_bp.route("", methods=["GET", "POST"])
def root():
    match rq.method:
        case "GET": response = service.read()
        case "POST": response = service.create()
    return response

@replace_bp.route("/request", methods=["GET", "POST"])
def request():
    match rq.method:
        case "GET": response = rq_service.read()
        case "POST": response = rq_service.create()
    return response
    