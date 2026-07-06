from flask import request, Blueprint
from services.reservas_tecnicas import FloaterService

floaters_bp = Blueprint("Reservas Tecnicas", __name__)
service = FloaterService()

@floaters_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def root():
    match request.method:
        case "GET": return service.read()
        case "POST": return service.add()
        case "DELETE": return service.remove()