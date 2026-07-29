from flask import Blueprint, request

from services.estrutura import StructureService


structure_bp = Blueprint("Estrutura", __name__)
service = StructureService()


@structure_bp.route("", methods=["GET", "POST", "DELETE"])
def root():
    if request.method == "GET":
        return service.read()
    if request.method == "POST":
        return service.create()
    return service.delete()
