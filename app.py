from gevent import monkey; monkey.patch_all() # Importante manter em primeira instancia
from flask import Flask, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from os import getenv
from utils.blueprints import blueprints
from utils.socket import socketio
from utils.db import db
from utils.permissions import enforce_request_permission
from utils.auth_guard import enforce_auth_state
from utils.openapi import build_openapi_spec
load_dotenv()  # Carrega o dotenv

# Variaveis de Instancia - SandBox()
DEBUG = getenv("DEBUG")
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

for bp in blueprints: app.register_blueprint(bp, url_prefix=blueprints[bp]) # Carrega os BPS das Rotas
db.init_app(app)  # Inicia o banco de dados
with app.app_context():
    db.create_all()  # Cria as tabelas
    from services.noticias import seed_default_news
    seed_default_news()

@app.route("/")
@app.route("/docs")
def index(): return render_template("index.html")

@app.get("/openapi.json")
def openapi_spec(): return jsonify(build_openapi_spec(app))

# Inicia o servidor
if __name__ == "__main__": socketio.run(app, debug=DEBUG, port=PORT, host=HOST)
