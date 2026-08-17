# Rotas HTTP de filiais.
# Dependências externas.
from flask import Blueprint, request

# Módulos internos da aplicação.
from services.filiais import BranchService


branch_bp = Blueprint("Filiais", __name__)
service = BranchService()


# Encaminha a requisição para o fluxo principal do módulo.
@branch_bp.route("", methods=["GET", "POST", "PATCH"])
def root():
    if request.method == "GET":
        return service.read()
    if request.method == "POST":
        return service.create()
    return service.update()


@branch_bp.get("/opcoes")
def options():
    return service.options()
