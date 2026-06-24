from flask import request, Blueprint
from services.usuarios import UserServices

user_bp = Blueprint("Usuarios", __name__)
service = UserServices()

@user_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def root():
    match request.method:
        case "GET": response = service.read()
        case "POST": response = service.create()
        case "PATCH": response = service.update()
        case "DELETE": response = service.delete()
    return response