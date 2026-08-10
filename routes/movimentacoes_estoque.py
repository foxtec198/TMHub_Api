from flask import request, Blueprint
from services.movimentos import MovementService

movimentos_bp = Blueprint("Movimentações de Estoque", __name__)
movement_service = MovementService()

@movimentos_bp.route("", methods=["GET", "POST"])
def movimentos_root():
    match request.method:
        case "GET": return movement_service.read()
        case "POST": return movement_service.create()
        
@movimentos_bp.get("/dashboard")
def movements_dashboard():
    return movement_service.dashboard()


@movimentos_bp.route("/<int:id>", methods=["PATCH", "DELETE"])
def movimentos_by_id(id):
    if request.method == "PATCH":
        return movement_service.update(id)
    return movement_service.delete(id)
