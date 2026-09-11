"""
========================================================================
========================================================================
=========   Dev by ["Guilherme Breve", "Bryan Ribeiro"] ================
========================================================================
========================================================================

"""

# Precisa acontecer antes dos demais imports (WebSocket).
from gevent import monkey; monkey.patch_all()  

# =============================================== Utils
from flask import Flask, g, jsonify, render_template, request
from utils.permissions import enforce_request_permission
from utils.auth_guard import enforce_auth_state
from utils.openapi import build_openapi_spec
from migrations import initialize_database
from utils.token import decode_token
from utils.safe_route import ( 
    MUTATION_METHODS, 
    _data_channel, 
    _emit_data_change
)
from utils.blueprints import blueprints
from utils.limiter import limiter
from utils.socket import socketio
from dotenv import load_dotenv
from flask_cors import CORS
from utils.db import db
from tqdm import tqdm
from os import getenv
import redis

# =============================================== Services
from services.avaliacoes_experiencia import ExperienceEvaluationService
from services.exames_periodicos import PeriodicExamService
from services.dashboard_ql import QLDashboardService
from services.uso_tmhub import TMHubUsageService
from services.tickets import TicketService

load_dotenv()  # Carrega o dotenv

DEBUG = getenv("DEBUG", "false").strip().lower() == "true"
PORT = int(getenv("PORT", 8590))
HOST = getenv("HOST", "0.0.0.0")

app = Flask(__name__)
socketio.init_app(app, cors_allowed_origins="*", async_mode="gevent")
limiter.init_app(app)

# Carrega os CORS security
CORS(app, allow_headers=["*"], supports_credentials=True) 

# Configs do APP
app.config["SECRET_KEY"] = getenv("SECRET")
app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DB_URI")

app.before_request(enforce_auth_state)
app.before_request(enforce_request_permission)

for bp, url_prefix in blueprints.items():
    app.register_blueprint(bp, url_prefix=url_prefix)

REALTIME_NOTIFICATION_EXCLUSIONS = {
    "/login",
    "/rpa/command",
    "/tm-ops/login",
}

@app.after_request
def emit_realtime_data_change(response):
    if (
        getattr(g, "tmhub_data_change_emitted", False)
        or request.method not in MUTATION_METHODS
        or response.status_code >= 400
    ):
        return response

    normalized_path = request.path.rstrip("/") or "/"
    if normalized_path in REALTIME_NOTIFICATION_EXCLUSIONS: return response

    token_data = {}
    access_token = request.headers.get("Access-Token")
    if access_token:
        try: token_data = decode_token(access_token) or {}
        except Exception: token_data = {}

    TMHubUsageService.record_successful_mutation(
        token_data,
        normalized_path,
        request.method,
    )

    channel = _data_channel(normalized_path, request.method)
    if not channel: return response

    _emit_data_change(token_data, channel)
    return response

db.init_app(app)  # Inicia o banco de dados
initialize_database(app) # Executa migrations

# Background Tasks =====================================
def ticket_sla_monitor():
    """Atualiza atrasos sem depender de alguém abrir a tela de chamados."""
    while True:
        try:
            with app.app_context():
                TicketService._refresh_overdue()
        except Exception:
            app.logger.exception("Falha ao atualizar SLA dos chamados")
        socketio.sleep(60)

def experience_evaluation_monitor():
    """Abre tarefas de experiência e marca atrasos sem depender da interface."""
    while True:
        try:
            with app.app_context():
                ExperienceEvaluationService.process_pending_tasks()
        except Exception:
            app.logger.exception("Falha ao processar avaliações de experiência")
        socketio.sleep(60 * 60)

def periodic_exam_monitor():
    """Promove para pendente os exames do mês subsequente sem depender da tela."""
    while True:
        try:
            with app.app_context():
                PeriodicExamService.refresh_pending_statuses()
        except Exception:
            app.logger.exception("Falha ao atualizar pendências de exames periódicos")
        socketio.sleep(60 * 60)

def ql_snapshot_monitor():
    """Mantém a fotografia do dia atual até o fechamento do dia útil."""
    while True:
        try:
            with app.app_context():
                changed = QLDashboardService.capture_daily()
                if changed:
                    socketio.emit("ql_update", {"action": "snapshot_updated"})
        except Exception:
            app.logger.exception("Falha ao registrar histórico diário de QL")
        socketio.sleep(900)

tasks = [
    {"task": ql_snapshot_monitor, "active": True},
    {"task": periodic_exam_monitor, "active": True},
    {"task": ticket_sla_monitor, "active": True},
    {"task": experience_evaluation_monitor, "active": True},
]

for item in tqdm(tasks, desc="Sincronizandp tarefas em segundo plano"):
    task = item["task"]
    active = item["active"]
    if task and active: socketio.start_background_task(task)

# End Background Tasks =====================================

@app.route("/")
@app.route("/docs")
def index(): return render_template("index.html")

@app.get("/openapi.json")
def openapi_spec(): return jsonify(build_openapi_spec(app))

# Inicia o servidor
if __name__ == "__main__": socketio.run(app, debug=DEBUG, port=PORT, host=HOST)
