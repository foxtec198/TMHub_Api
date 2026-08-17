# Rotas HTTP de autenticação.
# Dependências externas.
from flask import request, Blueprint
# Módulos internos da aplicação.
from services.auth import AuthService

auth_bp = Blueprint("Autenticador", __name__)
service = AuthService()

# Encaminha a requisição para o fluxo principal do módulo.
@auth_bp.route("", methods=["POST"])
def root(): return service.login()
