# Rotas HTTP de estrutura.
# Dependências externas.
from flask import Blueprint, request

# Módulos internos da aplicação.
from services.estrutura import StructureService


structure_bp = Blueprint("Estrutura", __name__)
service = StructureService()


# Encaminha a requisição para o fluxo principal do módulo.
@structure_bp.route("", methods=["GET", "POST", "DELETE"])
def root():
    if request.method == "GET":
        return service.read()
    if request.method == "POST":
        return service.create()
    return service.delete()


@structure_bp.get("/supervisores")
def supervisors():
    return service.read_supervisors()


@structure_bp.patch("/contratos/<int:center_id>/supervisor")
def update_contract_supervisor(center_id):
    return service.update_contract_supervisor(center_id)


@structure_bp.patch("/contratos/<int:center_id>/empresa")
def update_contract_company(center_id):
    return service.update_contract_company(center_id)


@structure_bp.patch("/locais/<int:location_id>")
def update_location(location_id):
    return service.update_location(location_id)
