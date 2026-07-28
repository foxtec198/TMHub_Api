from flask import Blueprint, request

from services.estrutura import StructureService


structure_bp = Blueprint("Estrutura", __name__)
service = StructureService()


@structure_bp.route("", methods=["GET", "POST"])
def root():
    if request.method == "GET":
        return service.read()
    return service.create()
