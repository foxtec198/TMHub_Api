from flask import request, Blueprint
from estoque.services.produtos import ProductsServices

produtos_bp = Blueprint("Produtos", __name__)
service = ProductsServices()

@produtos_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def root():
    match request.method:
        case "GET": return service.read()
        case "POST": return service.create()
        case "PATCH": return service.update()
        case "DELETE": return service.delete()