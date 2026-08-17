# Rotas HTTP de reservas técnicas.
# Dependências externas.
from flask import request, Blueprint
# Módulos internos da aplicação.
from services.reservas_tecnicas import FloaterService

floaters_bp = Blueprint("Reservas Tecnicas", __name__)
service = FloaterService()

# Encaminha a requisição para o fluxo principal do módulo.
@floaters_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def root():
    match request.method:
        case "GET": return service.read()
        case "POST": return service.add()
        case "PATCH": return service.update()
        case "DELETE": return service.remove()
