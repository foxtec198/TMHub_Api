# Rotas HTTP de PCD.
# Dependências externas.
from flask import request, Blueprint
# Módulos internos da aplicação.
from services.pcd import PcdService

pcd_bp = Blueprint("Pcd", __name__)
service = PcdService()

# Encaminha a requisição para o fluxo principal do módulo.
@pcd_bp.route("", methods=["GET", "PATCH"])
def root():
    match request.method:
        case "GET": return service.read()
        case "PATCH": return service.update()

@pcd_bp.post("/importar")
def importar():
    return service.import_xlsx()

@pcd_bp.delete("/todos")
def excluir_todos():
    return service.delete_all()
