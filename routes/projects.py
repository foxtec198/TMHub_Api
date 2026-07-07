from flask import Blueprint, request as rq
from services.projetos import ProjectService

project_bp = Blueprint("Projetos", __name__)
service = ProjectService()

@project_bp.route("", methods=["GET", "POST", "PATCH"])
def root():
    match rq.method:
        case "GET": response = service.read()
        case "POST": response = service.create()
        case "PATCH": response = service.update()
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
