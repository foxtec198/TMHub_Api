from flask import request, Blueprint
from services.reposicao import ReplaceService, RequestService

replace_bp = Blueprint("Reposições", __name__)
service = ReplaceService()
rq_service = RequestService()

@replace_bp.route("", methods=["GET", "POST"])
def root():
    match request.method:
        case "GET": response = service.read()
        case "POST": response = service.create()
    return response

@replace_bp.route("/requisicao", methods=["GET", "POST"])
def request():
    match request.method:
        case "GET": response = service.read()
        case "POST": response = service.create()
    return response
    