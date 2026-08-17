# Rotas HTTP de supervisores.
# Dependências externas.
from flask import request, Blueprint
# Módulos internos da aplicação.
from services.supervisores import ServiceSupervisors

supervisores_bp = Blueprint("Supervisores", __name__)
service = ServiceSupervisors()

# Encaminha a requisição para o fluxo principal do módulo.
@supervisores_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def root():
    match request.method:
        case "GET": return service.read()
        case "POST": return service.create()
        case "PATCH": return service.update()
        case "DELETE": return service.delete()
