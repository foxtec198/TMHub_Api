from flask import request, Blueprint
from services.admissao import VacancyService

admissao_bp = Blueprint("Admissão", __name__)
service = VacancyService()

@admissao_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def vagas_root():
    match request.method:
        case "GET": return service.read()
        case "POST": return service.create()
        case "PATCH": return service.update()
        case "DELETE": return service.delete()

@admissao_bp.route("/colaboradores", methods=["GET"])
def vagas_colaboradores():
    return service.search()
