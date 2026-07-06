from flask import request, Blueprint
from services.movimentos import MovementService

movimentos_bp = Blueprint("Movimentos de Estoque", __name__)
movement_service = MovementService()

@movimentos_bp.route("", methods=["GET", "POST"])
def movimentos_root():
    match request.method:
        case "GET": return movement_service.read()
        case "POST": return movement_service.create()
        
@movimentos_bp.route("/<int:id>", methods=["DELETE"])
def movimentos_by_id(id):
    return movement_service.delete(id)
