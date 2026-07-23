from flask import Blueprint, request

from services.glosas import DisallowanceService


disallowance_bp = Blueprint("Controle de Glosas", __name__)
service = DisallowanceService()


@disallowance_bp.route("", methods=["GET", "POST", "PATCH", "DELETE"])
def root():
    match request.method:
        case "GET":
            return service.read()
        case "POST":
            return service.create()
        case "PATCH":
            return service.update()
        case "DELETE":
            return service.delete()
