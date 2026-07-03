from flask import Blueprint, jsonify, request as rq
from utils.socket import socketio

rpa_bp = Blueprint("RPAs", __name__)
agents = {}

@rpa_bp.route("/command", methods=["POST"])
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
