from flask import request, Blueprint
from services.supervisores import ServiceSupervisors

supervisores_bp = Blueprint("Supervisores", __name__)
service = ServiceSupervisors()

@supervisores_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def root():
    match request.method:
        case "GET": response = service.read()
        case "POST": response = service.create()
        case "PATCH": response = service.update()
        case "DELETE": response = service.delete()
    return response