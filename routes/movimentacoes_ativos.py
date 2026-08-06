from flask import Blueprint, request

from services.movimentacoes_ativos import StructureAssetMovementService


asset_movements_bp = Blueprint("Movimentações de Ativos", __name__)
service = StructureAssetMovementService()


@asset_movements_bp.route("", methods=["GET", "POST"])
def root():
    if request.method == "GET":
        return service.read()
    return service.create()