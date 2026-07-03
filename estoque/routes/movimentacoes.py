from flask import request, Blueprint
from estoque.services.movimentacoes import MovementsServices

movimentacoes_bp = Blueprint("Movimentacoes", __name__)
service = MovementsServices()

@movimentacoes_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def root():
    match request.method:
        case "GET": return service.read()
        case "POST": return service.create()
        case "PATCH": return service.update()
        case "DELETE": return service.delete()
