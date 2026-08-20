# Inicializa a aplicação Flask do TM Hub.
# Dependências externas.
from gevent import monkey; monkey.patch_all()  # Importante manter em primeira instancia

from flask import Flask, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
# Biblioteca padrão.
from os import getenv
# Dependências externas.
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
# Módulos internos da aplicação.
from utils.blueprints import blueprints
from utils.socket import socketio
from utils.db import db
from utils.permissions import enforce_request_permission
from utils.auth_guard import enforce_auth_state
from utils.openapi import build_openapi_spec
from services.tickets import TicketService
from services.avaliacoes_experiencia import ExperienceEvaluationService
from services.dashboard_ql import QLDashboardService

load_dotenv()  # Carrega o dotenv

# Variaveis de Instancia - SandBox()
DEBUG = DEBUG = getenv("DEBUG", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
PORT = int(getenv("PORT", 8590))
HOST = getenv("HOST")

# Variaveis Comuns
agents = {}
app = Flask(__name__)
socketio.init_app(app, cors_allowed_origins="*", async_mode="gevent")
CORS(app, allow_headers="*")  # Carrega os CORS security

# Configs do APP
app.config["SECRET_KEY"] = getenv("SECRET")
app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DB_URI")

app.before_request(enforce_auth_state)
app.before_request(enforce_request_permission)

for bp in blueprints: app.register_blueprint(bp, url_prefix=blueprints[bp])  # Carrega os BPS das Rotas

db.init_app(app)  # Inicia o banco de dados

with app.app_context():
    db.create_all()  # Cria as tabelas
    user_columns = {column["name"] for column in inspect(db.engine).get_columns("usuarios")}
    if "modo_tema" not in user_columns:
        # Migração aditiva para instalações existentes sem Alembic.
        try:
            with db.engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE usuarios ADD COLUMN modo_tema VARCHAR(5) NOT NULL DEFAULT 'light'"
                ))
                connection.execute(text(
                    "UPDATE usuarios SET modo_tema = CASE WHEN LOWER(tema) = 'dark' THEN 'dark' ELSE 'light' END"
                ))
                connection.execute(text(
                    "UPDATE usuarios SET tema = 'tmhub' WHERE LOWER(tema) IN ('light', 'dark')"
                ))
        except SQLAlchemyError:
            # Outro worker pode ter concluído a mesma migração em paralelo.
            refreshed_columns = {
                column["name"] for column in inspect(db.engine).get_columns("usuarios")
            }
            if "modo_tema" not in refreshed_columns:
                raise

    user_columns = {column["name"] for column in inspect(db.engine).get_columns("usuarios")}
    if "timo_ativo" not in user_columns:
        # Migração aditiva: a preferência pertence ao perfil e começa desativada.
        try:
            with db.engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE usuarios ADD COLUMN timo_ativo BOOLEAN NOT NULL DEFAULT FALSE"
                ))
        except SQLAlchemyError:
            # Em múltiplos workers, outro processo pode concluir a alteração antes.
            refreshed_columns = {
                column["name"] for column in inspect(db.engine).get_columns("usuarios")
            }
            if "timo_ativo" not in refreshed_columns:
                raise

    requisition_tables = set(inspect(db.engine).get_table_names())
    if "rp_requisicoes" in requisition_tables:
        requisition_columns = {
            column["name"] for column in inspect(db.engine).get_columns("rp_requisicoes")
        }
        if "origem" not in requisition_columns:
            # A origem precisa ser persistida: uma requisição normal também
            # pode ter registro em controle_faltas, então esse relacionamento
            # isoladamente não identifica a fonte da solicitação.
            try:
                with db.engine.begin() as connection:
                    connection.execute(text(
                        "ALTER TABLE rp_requisicoes "
                        "ADD COLUMN origem VARCHAR(30) NOT NULL DEFAULT 'requisicao'"
                    ))
                    connection.execute(text(
                        "CREATE INDEX IF NOT EXISTS ix_rp_requisicoes_origem "
                        "ON rp_requisicoes (origem)"
                    ))
                    connection.execute(text(
                        "UPDATE rp_requisicoes requisicao "
                        "SET origem = 'controle_faltas' "
                        "WHERE EXISTS ("
                        "  SELECT 1 FROM rp_timeline timeline "
                        "  WHERE timeline.requisicao_id = requisicao.id "
                        "  AND timeline.tipo = 'Requisição criada através do Controle de Faltas'"
                        ")"
                    ))
            except SQLAlchemyError:
                refreshed_columns = {
                    column["name"] for column in inspect(db.engine).get_columns("rp_requisicoes")
                }
                if "origem" not in refreshed_columns:
                    raise

    department_configuration_tables = set(inspect(db.engine).get_table_names())
    if "configuracoes_departamentos" in department_configuration_tables:
        department_columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("configuracoes_departamentos")
        }
        if "capacidade_pessoas" not in department_columns:
            # A meta passou a pertencer ao departamento. Mantemos a coluna
            # legada nos centros e aproveitamos sua soma como ponto de partida.
            try:
                with db.engine.begin() as connection:
                    connection.execute(text(
                        "ALTER TABLE configuracoes_departamentos "
                        "ADD COLUMN capacidade_pessoas INTEGER"
                    ))
                    connection.execute(text(
                        "INSERT INTO configuracoes_departamentos "
                        "(departamento, ativo, capacidade_pessoas) "
                        "SELECT departamento, TRUE, SUM(capacidade_pessoas)::INTEGER "
                        "FROM centro_de_custo "
                        "WHERE departamento IS NOT NULL AND capacidade_pessoas IS NOT NULL "
                        "GROUP BY departamento "
                        "ON CONFLICT (departamento) DO UPDATE SET "
                        "capacidade_pessoas = EXCLUDED.capacidade_pessoas "
                        "WHERE configuracoes_departamentos.capacidade_pessoas IS NULL"
                    ))
            except SQLAlchemyError:
                refreshed_columns = {
                    column["name"]
                    for column in inspect(db.engine).get_columns("configuracoes_departamentos")
                }
                if "capacidade_pessoas" not in refreshed_columns:
                    raise

    tables = set(inspect(db.engine).get_table_names())
    if "timo_configuracoes" in tables:
        timo_columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("timo_configuracoes")
        }
        timo_migrations = (
            ("titulo", "ALTER TABLE timo_configuracoes ADD COLUMN titulo VARCHAR(150)"),
            ("descricao", "ALTER TABLE timo_configuracoes ADD COLUMN descricao TEXT"),
            ("personalizado", "ALTER TABLE timo_configuracoes ADD COLUMN personalizado BOOLEAN NOT NULL DEFAULT FALSE"),
        )
        for column_name, statement in timo_migrations:
            if column_name in timo_columns:
                continue
            try:
                with db.engine.begin() as connection:
                    connection.execute(text(statement))
            except SQLAlchemyError:
                refreshed_columns = {
                    column["name"]
                    for column in inspect(db.engine).get_columns("timo_configuracoes")
                }
                if column_name not in refreshed_columns:
                    raise
            timo_columns.add(column_name)

    floater_columns = {column["name"] for column in inspect(db.engine).get_columns("volantes")}
    floater_migrations = (
        ("disponivel", "ALTER TABLE volantes ADD COLUMN disponivel BOOLEAN NOT NULL DEFAULT TRUE"),
        ("indisponibilidade_motivo", "ALTER TABLE volantes ADD COLUMN indisponibilidade_motivo VARCHAR(12)"),
        ("indisponivel_em", "ALTER TABLE volantes ADD COLUMN indisponivel_em TIMESTAMP"),
    )
    for column_name, statement in floater_migrations:
        if column_name in floater_columns:
            continue
        try:
            with db.engine.begin() as connection:
                connection.execute(text(statement))
        except SQLAlchemyError:
            refreshed_columns = {
                column["name"] for column in inspect(db.engine).get_columns("volantes")
            }
            if column_name not in refreshed_columns:
                raise
        floater_columns.add(column_name)

    ticket_tables = set(inspect(db.engine).get_table_names())
    if "tc_historico" in ticket_tables:
        ticket_columns = {
            column["name"] for column in inspect(db.engine).get_columns("tc_historico")
        }
        if "filial_id" not in ticket_columns:
            try:
                with db.engine.begin() as connection:
                    connection.execute(text(
                        "ALTER TABLE tc_historico ADD COLUMN filial_id INTEGER REFERENCES filiais(id) ON DELETE SET NULL"
                    ))
                    connection.execute(text(
                        "CREATE INDEX IF NOT EXISTS ix_tc_historico_filial_id ON tc_historico (filial_id)"
                    ))
                    connection.execute(text(
                        "UPDATE tc_historico ticket "
                        "SET filial_id = ("
                        "  SELECT MIN(link.filial_id) FROM filial_usuarios link "
                        "  WHERE link.usuario_id = ticket.created_by"
                        ") "
                        "WHERE ticket.filial_id IS NULL AND ticket.created_by IS NOT NULL"
                    ))
            except SQLAlchemyError:
                refreshed_columns = {
                    column["name"] for column in inspect(db.engine).get_columns("tc_historico")
                }
                if "filial_id" not in refreshed_columns:
                    raise


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
if __name__ == "__main__": socketio.run(app, debug=DEBUG, port=PORT, host=HOST)
