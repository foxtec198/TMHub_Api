# Rotas HTTP de funcionários.
# Dependências externas.
from flask import request, Blueprint
# Módulos internos da aplicação.
from services.funcionarios import EmployeesService

funcionarios_bp = Blueprint("Funcionarios", __name__)
service = EmployeesService()

# Encaminha a requisição para o fluxo principal do módulo.
@funcionarios_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def root():
    match request.method:
        case "GET": return service.read()
        case "POST": return service.create()
        case "PATCH": return service.update()
        case "DELETE": return service.delete()
