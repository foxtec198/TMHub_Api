from flask import request, Blueprint
from services.categorias import CategoryService

categorias_bp = Blueprint("Categorias de Produtos", __name__)
category_service = CategoryService()

@categorias_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def categorias_root():
    match request.method:
        case "GET": return category_service.read()
        case "POST": return category_service.create()
        case "PATCH": return category_service.update()
        case "DELETE": return category_service.delete()

