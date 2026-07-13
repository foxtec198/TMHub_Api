from services.reposicoes import HistoryService, RequestService, TimelineService
from flask import Blueprint, request as rq

replace_bp = Blueprint("Reposições", __name__)

history_service = HistoryService()
rq_service = RequestService()
timeline_service = TimelineService()

# Approve or reprove a request and persist its history entry.
@replace_bp.route("", methods=["POST"])
def root(): return history_service.create()

# History period queries and maintenance operations.
@replace_bp.route("/history", methods=["POST", "PATCH", "DELETE"])
def history():
    match rq.method:
        case "POST": return history_service.read()
        case "PATCH": return history_service.update()
        case "DELETE": return history_service.delete()

# Open requisition queue CRUD.
@replace_bp.route("/request", methods=["GET", "POST", "PATCH", "DELETE"])
def request():
    match rq.method:
        case "GET": return rq_service.read()
        case "POST": return rq_service.create()
        case "PATCH": return rq_service.update()
        case "DELETE": return rq_service.delete()

@replace_bp.get("/request/export")
def export_requests(): return rq_service.export()

# Spreadsheet template and transactional bulk import endpoints.
@replace_bp.get("/request/modelo-importacao")
def download_request_import_template(): return rq_service.download_import_template()

@replace_bp.post("/request/importar")
def import_requests(): return rq_service.import_requests()

@replace_bp.get("/reservas-uso")
def daily_reservations(): return rq_service.daily_reservations()

# Request audit timeline.
@replace_bp.route("/timeline", methods=["GET"])
def timeline(): return timeline_service.read()
