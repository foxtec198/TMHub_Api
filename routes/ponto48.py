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


@ponto48_bp.post("/importar/chunk")
def upload_import_chunk():
    return service.upload_import_chunk()


@ponto48_bp.post("/importar/finalizar")
def finalize_chunked_import():
    return service.finalize_chunked_import()


@ponto48_bp.delete("/importar")
def delete_imported_data():
    return service.delete_imported_data()


@ponto48_bp.get("/ajustes")
def adjustments_dashboard():
    return service.adjustments_dashboard()


@ponto48_bp.post("/ajustes/importar")
def import_adjustments():
    return service.import_adjustments()


@ponto48_bp.get("/espelho")
def mirror_dashboard():
    return service.mirror_dashboard()
