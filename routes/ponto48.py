from flask import Blueprint

from services.ponto48 import Ponto48Service


ponto48_bp = Blueprint("Ponto48", __name__)
service = Ponto48Service()


@ponto48_bp.get("")
def dashboard():
    return service.dashboard()


@ponto48_bp.post("/importar")
def import_files():
    return service.import_files()
