from flask import Blueprint, request as rq
from services.projetos import ProjectService

project_bp = Blueprint("Projetos", __name__)
service = ProjectService()

@project_bp.route("", methods=["GET", "POST"])
def root():
    match rq.method:
        case "GET": response = service.read()
        case "POST": response = service.create()
    return response