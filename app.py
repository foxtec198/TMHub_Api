from gevent import monkey; monkey.patch_all()  # Importante manter em primeira instancia

from flask import Flask, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from os import getenv
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from utils.blueprints import blueprints
from utils.socket import socketio
from utils.db import db
from utils.permissions import enforce_request_permission
from utils.auth_guard import enforce_auth_state
from utils.openapi import build_openapi_spec

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

@app.route("/")
@app.route("/docs")
def index():
    return render_template("index.html")


@app.get("/openapi.json")
def openapi_spec():
    return jsonify(build_openapi_spec(app))


# Inicia o servidor
if __name__ == "__main__": socketio.run(app, debug=DEBUG, port=PORT, host=HOST)
