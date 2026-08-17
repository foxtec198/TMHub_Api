# Rotas HTTP de automação RPA.
# Dependências externas.
from flask import Blueprint, jsonify, request as rq
# Módulos internos da aplicação.
from utils.socket import socketio

rpa_bp = Blueprint("RPAs", __name__)
agents = {}


def unregister_rpa_agent(sid):
    """Remove a sessão do RPA no único dispatcher global de disconnect."""
    for agent_id, current_sid in list(agents.items()):
        if current_sid == sid:
            del agents[agent_id]

@rpa_bp.route("/command", methods=["POST"])
def set_command():
    bd = rq.get_json()
    agent_id = bd.get("agent_id")
    command = bd.get("command")
    
    if agent_id in agents:
        sid = agents[agent_id]
        if not socketio.server.manager.is_connected(sid, namespace="/"):
            unregister_rpa_agent(sid)
            return jsonify({"error": "Agente offline"}), 404
        socketio.emit("command", command, to=sid)
        return jsonify({"ok": True}), 200
    return jsonify({"error": "Agente offline"}), 404

@socketio.on("register") # Registra um novo AGENTE
def on_register(data):
    agent_id = data["agent_id"]
    agents[agent_id] = rq.sid

@socketio.on("command_done")
def on_command_done(data):
    print(f"Agente {data['agent_id']} concluiu o comando: {data['status']}")
