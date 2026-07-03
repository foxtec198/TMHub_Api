from flask import request, Blueprint
from services.produtos import ProductService

produtos_bp = Blueprint("Produtos", __name__)
product_service = ProductService()

@produtos_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def produtos_root():
    match request.method:
        case "GET": return product_service.read()
        case "POST": return product_service.create()
        case "PATCH": return product_service.update()
        case "DELETE": return product_service.delete()

