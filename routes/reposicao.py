from services.reposicoes import HistoryService, RequestService, TimelineService
from flask import Blueprint, request as rq

replace_bp = Blueprint("Reposições", __name__)

history_service = HistoryService()
rq_service = RequestService()
timeline_service = TimelineService()

# Aprova ou reprova uma requisição e registra o respectivo histórico.
@replace_bp.route("", methods=["POST"])
def root(): return history_service.create()

# Consultas por período e operações de manutenção do histórico.
@replace_bp.route("/history", methods=["POST", "PATCH", "DELETE"])
def history():
    match rq.method:
        case "POST": return history_service.read()
        case "PATCH": return history_service.update()
        case "DELETE": return history_service.delete()

# CRUD da fila de requisições abertas.
@replace_bp.route("/request", methods=["GET", "POST", "PATCH", "DELETE"])
def request():
    match rq.method:
        case "GET": return rq_service.read()
        case "POST": return rq_service.create()
        case "PATCH": return rq_service.update()
        case "DELETE": return rq_service.delete()

@replace_bp.get("/request/solicitante")
def requester(): return rq_service.requester()

@replace_bp.get("/request/export")
def export_requests(): return rq_service.export()

@replace_bp.post("/request/contexto-disciplinar")
def disciplinary_context(): return rq_service.disciplinary_context()

@replace_bp.post("/request/contexto-adicional")
def additional_context(): return rq_service.additional_context()

@replace_bp.get("/kds")
def kds_requests(): return rq_service.kds()

# Rotas do modelo de planilha e da importação transacional em lote.
@replace_bp.get("/request/modelo-importacao")
def download_request_import_template(): return rq_service.download_import_template()

@replace_bp.post("/request/importar")
def import_requests(): return rq_service.import_requests()

@replace_bp.get("/reservas-uso")
def daily_reservations(): return rq_service.daily_reservations()

# Timeline de auditoria da requisição.
@replace_bp.route("/timeline", methods=["GET"])
def timeline(): return timeline_service.read()
