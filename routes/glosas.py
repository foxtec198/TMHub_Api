from flask import Blueprint, request

from services.glosas import DisallowanceService
from services.rocada_glosas import RocadaDisallowanceService


disallowance_bp = Blueprint("Controle de Glosas", __name__)
disallowance_files_bp = Blueprint("Evidências de Glosas", __name__)
service = DisallowanceService()
rocada_service = RocadaDisallowanceService()


@disallowance_bp.get("/rocada")
def rocada():
    return rocada_service.read()


@disallowance_bp.get("/rocada/detalhe")
def rocada_detail():
    return rocada_service.detail()


@disallowance_bp.get("/rocada/dashboard")
def rocada_dashboard():
    return rocada_service.dashboard()


@disallowance_bp.get("/rocada/dashboard/detalhe")
def rocada_dashboard_detail():
    return rocada_service.dashboard_detail()


@disallowance_bp.post("/rocada/importar-ponto")
def rocada_import_mirror():
    return rocada_service.import_mirror()


@disallowance_bp.get("/dashboard")
def dashboard():
    return service.dashboard()


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


@disallowance_bp.get("/export")
def export():
    return service.export()


@disallowance_bp.route("/<int:glosa_id>/evidencia", methods=["POST", "DELETE"])
def evidence(glosa_id):
    if request.method == "POST":
        return service.upload_evidence(glosa_id)
    return service.remove_evidence(glosa_id)


@disallowance_files_bp.get("/<path:filename>")
def public_evidence(filename):
    return service.serve_evidence(filename)
