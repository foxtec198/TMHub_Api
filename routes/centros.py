from flask import request, Blueprint
from services.centros import CostsCenterService

center_bp = Blueprint("Centros de Custo", __name__)
service = CostsCenterService()

@center_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def root():
    match request.method:
        case "GET": response = service.read()
        case "POST": response = service.create()
        case "PATCH": response = service.update()
        case "DELETE": response = service.delete()
    return response