from flask import request, Blueprint
from services.auth import AuthService

auth_bp = Blueprint("Autenticador", __name__)
service = AuthService()

@auth_bp.route("", methods=["POST"])
def root(): return service.login()