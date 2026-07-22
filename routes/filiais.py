from flask import Blueprint, request

from services.filiais import BranchService


branch_bp = Blueprint("Filiais", __name__)
service = BranchService()


@branch_bp.route("", methods=["GET", "POST", "PATCH"])
def root():
    if request.method == "GET":
        return service.read()
    if request.method == "POST":
        return service.create()
    return service.update()


@branch_bp.get("/opcoes")
def options():
    return service.options()
