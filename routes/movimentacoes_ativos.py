# Rotas HTTP de movimentações de ativos.
# Dependências externas.
from flask import Blueprint, request

# Módulos internos da aplicação.
from services.movimentacoes_ativos import StructureAssetMovementService


asset_movements_bp = Blueprint("Movimentações de Ativos", __name__)
service = StructureAssetMovementService()


# Encaminha a requisição para o fluxo principal do módulo.
@asset_movements_bp.route("", methods=["GET", "POST"])
def root():
    if request.method == "GET":
        return service.read()
    return service.create()
