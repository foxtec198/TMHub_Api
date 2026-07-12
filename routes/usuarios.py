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

@user_bp.get("/perfil")
def profile(): return service.profile()

@user_bp.patch("/perfil")
def update_profile(): return service.update_profile()

@user_bp.post("/email/codigo")
def request_email_code(): return service.request_email_code()

@user_bp.post("/email/confirmar")
def confirm_email(): return service.confirm_email()
