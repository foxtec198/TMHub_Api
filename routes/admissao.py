from flask import request, Blueprint
from services.admissao import VacancyService

admissao_bp = Blueprint("Admissão", __name__)
service = VacancyService()

# O endpoint raiz mantém o contrato REST já consumido pela tela de vagas.
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

@admissao_bp.route("/horarios", methods=["GET"])
def vagas_horarios():
    return service.search_schedules()

@admissao_bp.route("/historico-entrevistas", methods=["GET"])
def historico_entrevistas():
    return service.read_interview_history()

@admissao_bp.route("/dashboard", methods=["GET"])
def dashboard_admissoes():
    """Expõe os indicadores consolidados protegidos pela autenticação do serviço."""
    return service.admission_dashboard()
