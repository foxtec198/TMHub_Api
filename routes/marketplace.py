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


@marketplace_bp.post("/compras")
def buy():
    return service.buy()
