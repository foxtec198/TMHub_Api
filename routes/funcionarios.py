from flask import request, Blueprint
from services.funcionarios import EmployeesService

funcionarios_bp = Blueprint("Funcionarios", __name__)
service = EmployeesService()

@funcionarios_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def root():
    match request.method:
        case "GET": return service.read()
        case "POST": return service.create()
        case "PATCH": return service.update()
        case "DELETE": return service.delete()