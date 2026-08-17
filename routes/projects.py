# Rotas HTTP de projetos.
# Dependências externas.
from flask import Blueprint, request as rq
# Módulos internos da aplicação.
from services.projetos import ProjectService

project_bp = Blueprint("Projetos", __name__)
service = ProjectService()


@project_bp.get("/dashboard")
def dashboard():
    return service.dashboard()

# Encaminha a requisição para o fluxo principal do módulo.
@project_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def root():
    match rq.method:
        case "GET": response = service.read()
        case "POST": response = service.create()
        case "PATCH": response = service.update()
        case "DELETE": response = service.delete()
    return response


@project_bp.route("/<project_id>/cards", methods=["POST"])
def cards(project_id):
    return service.create_card(project_id)


@project_bp.route("/cards/<card_id>", methods=["PATCH", "DELETE"])
def card(card_id):
    match rq.method:
        case "PATCH": response = service.update_card(card_id)
        case "DELETE": response = service.delete_card(card_id)
    return response


@project_bp.post("/cards/<int:card_id>/comentarios")
def create_comment(card_id):
    return service.create_comment(card_id)


@project_bp.route("/comentarios/<int:comment_id>", methods=["PATCH", "DELETE"])
def comment(comment_id):
    return (
        service.update_comment(comment_id)
        if rq.method == "PATCH"
        else service.delete_comment(comment_id)
    )


@project_bp.post("/cards/<int:card_id>/arquivos")
def upload_card_file(card_id):
    return service.upload_card_file(card_id)


@project_bp.route("/cards/<int:card_id>/arquivos/<int:file_id>", methods=["GET", "DELETE"])
def card_file(card_id, file_id):
    return (
        service.download_card_file(card_id, file_id)
        if rq.method == "GET"
        else service.delete_card_file(card_id, file_id)
    )
