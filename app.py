from flask import Flask, render_template, request as rq, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from os import getenv
from utils.blueprints import blueprints
from utils.db import db
from flask_socketio import SocketIO
load_dotenv()  # Carrega o dotenv

# Variaveis de Instancia
DEBUG = getenv("DEBUG")
PORT = getenv("PORT", 8590)
HOST = getenv("HOST")

# Variaveis Comuns
agents = {}
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")
CORS(app, allow_headers="*")  # Carrega os CORS security

# Configs do APP
app.config["SECRET_KEY"] = getenv("SECRET")
app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DB_URI")

# Carrega os BPS das Rotas
for bp in blueprints: app.register_blueprint(bp, url_prefix=blueprints[bp])
db.init_app(app)  # Inicia o banco de dados
with app.app_context(): db.create_all()  # Cria as tabelas

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/rpa/command", methods=["POST"])
def set_command():
    bd = rq.get_json()
    agent_id = bd.get("agent_id")
    command = bd.get("command")
    
    if agent_id in agents:
        socketio.emit("command", command, to=agents[agent_id])
        return jsonify({"ok": True}), 200
    return jsonify({"error": "Agente offline"}), 404


@socketio.on("register") # Registra um novo AGENTE
def on_register(data):
    agent_id = data["agent_id"]
    agents[agent_id] = rq.sid

@socketio.on("disconnect") # Ao desconectar um agente remove do sockets
def on_disconnect():
    for agent_id, sid in list(agents.items()):
        if sid == rq.sid: del agents[agent_id]

@socketio.on("command_done")
def on_command_done(data):
    print(f"Agente {data['agent_id']} concluiu o comando: {data['status']}")

# Inicia o servidor
if __name__ == "__main__":
    socketio.run(app, debug=DEBUG, port=PORT, host=HOST)
