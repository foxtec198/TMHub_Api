from flask import Blueprint

from services.marketplace import MarketplaceService

marketplace_bp = Blueprint("Marketplace", __name__)
service = MarketplaceService()


@marketplace_bp.get("")
def catalog():
    return service.catalog()


@marketplace_bp.get("/compras")
def purchases():
    return service.purchases()


@marketplace_bp.get("/adornos")
def owned_adornments():
    return service.owned_adornments()


@marketplace_bp.get("/cenarios")
def owned_scenarios():
    return service.owned_scenarios()


@marketplace_bp.post("/compras")
def buy():
    return service.checkout()


@marketplace_bp.post("/checkout")
def checkout():
    return service.checkout()


@marketplace_bp.post("/compras/<int:purchase_id>/reembolso")
def refund(purchase_id):
    return service.refund(purchase_id=purchase_id)


@marketplace_bp.patch("/equipar")
def equip():
    return service.equip()
