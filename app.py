# Inicializa a aplicação Flask do TM Hub.
# Dependências externas.
from gevent import monkey

monkey.patch_all()  # Precisa acontecer antes dos demais imports.

from flask import Flask, g, jsonify, render_template, request
from flask_cors import CORS
from dotenv import load_dotenv
# Biblioteca padrão.
from os import getenv
# Módulos internos da aplicação.
from migrations import initialize_database
from utils.blueprints import blueprints
from utils.socket import socketio
from utils.db import db
from utils.permissions import enforce_request_permission
from utils.auth_guard import enforce_auth_state
from utils.openapi import build_openapi_spec
from utils.safe_route import MUTATION_METHODS, _data_channel, _emit_data_change
from utils.token import decode_token
from models.configuracoes_sistema import SystemConfiguration
from services.tickets import TicketService
from services.avaliacoes_experiencia import ExperienceEvaluationService
from services.dashboard_ql import QLDashboardService

load_dotenv()  # Carrega o dotenv

# Variaveis de Instancia - SandBox()
DEBUG = getenv("DEBUG", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
PORT = int(getenv("PORT", 8590))
HOST = getenv("HOST")

app = Flask(__name__)
socketio.init_app(app, cors_allowed_origins="*", async_mode="gevent")
CORS(app, allow_headers="*")  # Carrega os CORS security

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
    "/schedular/login",
}


@app.after_request
def emit_realtime_data_change(response):
    """Broadcast a lightweight update after successful mutations.

    The payload intentionally identifies only the affected module. Frontend
    clients can refresh their own data and optionally show a browser
    notification without receiving records that may belong to another user.
    """
    if (
        getattr(g, "tmhub_data_change_emitted", False)
        or request.method not in MUTATION_METHODS
        or response.status_code >= 400
    ):
        return response

    normalized_path = request.path.rstrip("/") or "/"
    if normalized_path in REALTIME_NOTIFICATION_EXCLUSIONS:
        return response

    channel = _data_channel(normalized_path, request.method)
    if not channel:
        return response

    token_data = {}
    access_token = request.headers.get("Access-Token")
    if access_token:
        try:
            token_data = decode_token(access_token) or {}
        except Exception:
            # Authentication already validated the request when a token was
            # required. Realtime is complementary, so a malformed optional
            # token must not alter a successful response.
            token_data = {}

    _emit_data_change(token_data, channel)
    return response

db.init_app(app)  # Inicia o banco de dados
initialize_database(app)


def ticket_sla_monitor():
    """Atualiza atrasos sem depender de alguém abrir a tela de chamados."""
    while True:
        try:
            with app.app_context():
                TicketService._refresh_overdue()
        except Exception:
            app.logger.exception("Falha ao atualizar SLA dos chamados")
        socketio.sleep(60)


socketio.start_background_task(ticket_sla_monitor)


def experience_evaluation_monitor():
    """Abre tarefas de experiência e marca atrasos sem depender da interface."""
    while True:
        try:
            with app.app_context():
                ExperienceEvaluationService.process_pending_tasks()
        except Exception:
            app.logger.exception("Falha ao processar avaliações de experiência")
        socketio.sleep(60 * 60)


socketio.start_background_task(experience_evaluation_monitor)


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


socketio.start_background_task(ql_snapshot_monitor)


@app.route("/")
@app.route("/docs")
def index():
    return render_template("index.html")


@app.get("/openapi.json")
def openapi_spec():
    return jsonify(build_openapi_spec(app))


# Inicia o servidor
if __name__ == "__main__":
    socketio.run(app, debug=DEBUG, port=PORT, host=HOST)
