from flask import request, Blueprint
from services.pcd import PcdService

pcd_bp = Blueprint("Pcd", __name__)
service = PcdService()

@pcd_bp.route("", methods=["GET", "PATCH"])
def root():
    match request.method:
        case "GET": return service.read()
        case "PATCH": return service.update()

@pcd_bp.post("/importar")
def importar():
    return service.import_xlsx()
