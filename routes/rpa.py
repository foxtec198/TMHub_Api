"""Registro, disponibilidade e despacho seguro dos agentes RPA."""

from flask import Blueprint, jsonify, request as rq

from utils.filial_scope import is_admin
from utils.permissions import has_permission
from utils.safe_route import safe_route
from utils.socket import socketio


rpa_bp = Blueprint("RPAs", __name__)
agents = {}
active_commands = {}

AGENT_CATALOG = (
    {
        "key": "pontomais-relatorios",
        "name": "Ponto Mais — Relatórios",
        "category": "Ponto Mais",
        "capability": "pontomais_report_import",
        "active": True,
        "description": "Baixa e importa relatórios web do Ponto Mais.",
    },
    {
        "key": "hk-bot",
        "name": "HK Bot",
        "category": "HK",
        "capability": "hk_adjust",
        "active": False,
        "description": "Inativo: depende de resolução, foco de tela e imagens de interface.",
    },
)


def _connected(entry):
    return bool(entry and socketio.server.manager.is_connected(entry["sid"], namespace="/"))


def unregister_rpa_agent(sid):
    """Remove a sessão do agente desconectado e publica apenas seu estado."""
    removed = [agent_id for agent_id, entry in agents.items() if entry["sid"] == sid]
    for agent_id in removed:
        agents.pop(agent_id, None)
    if removed:
        socketio.emit("rpa_agents_update", {"agent_ids": removed})


def _eligible_agents(capability, category=None):
    matches = []
    for agent_id, entry in list(agents.items()):
        if not _connected(entry):
            unregister_rpa_agent(entry["sid"])
            continue
        if capability not in entry["capabilities"]:
            continue
        if category and entry["category"] != category:
            continue
        matches.append((agent_id, entry))
    return matches


def send_command(agent_id, command):
    """Envia um comando a um agente conectado sem registrar conteúdo sensível."""
    entry = agents.get(str(agent_id))
    if not _connected(entry):
        if entry:
            unregister_rpa_agent(entry["sid"])
        return False, "Agente offline", None
    socketio.emit("command", command, to=entry["sid"])
    return True, None, str(agent_id)


def send_command_for_capability(capability, command, category=None):
    matches = _eligible_agents(capability, category)
    if not matches:
        return False, "Nenhum agente compatível está online.", None
    agent_id, entry = matches[0]
    socketio.emit("command", command, to=entry["sid"])
    return True, None, agent_id


def track_command(command_id, user_id, capability):
    active_commands[command_id] = {"user_id": user_id, "capability": capability, "agent_id": None}


def discard_command(command_id):
    active_commands.pop(command_id, None)


def _serialize_agents():
    response = []
    for item in AGENT_CATALOG:
        compatible = _eligible_agents(item["capability"], item["category"])
        response.append({
            **item,
            "online": bool(compatible),
            "available": bool(item["active"] and compatible),
            "machines": [agent_id for agent_id, _ in compatible],
        })
    return response


@rpa_bp.get("/agentes")
@safe_route
def list_agents(token_data):
    if not has_permission(token_data, "controle_jornadas", "view"):
        return jsonify("Você não possui acesso aos agentes RPA."), 403
    return jsonify({"agentes": _serialize_agents()}), 200


@rpa_bp.post("/command")
@safe_route
def set_command(token_data):
    if not is_admin(token_data):
        return jsonify({"error": "Apenas administradores podem disparar comandos RPA genéricos."}), 403
    body = rq.get_json(silent=True) or {}
    sent, error, _ = send_command(body.get("agent_id"), body.get("command") or {})
    return (jsonify({"ok": True}), 200) if sent else (jsonify({"error": error}), 404)


@socketio.on("register")
def on_register(data):
    data = data if isinstance(data, dict) else {}
    agent_id = str(data.get("agent_id") or "").strip()
    category = str(data.get("category") or "TM Hub").strip()[:80]
    capabilities = {str(item) for item in data.get("capabilities", []) if isinstance(item, str)}
    if not agent_id or not capabilities:
        socketio.server.disconnect(rq.sid, namespace="/")
        return False
    agents[agent_id] = {"sid": rq.sid, "category": category, "capabilities": capabilities}
    socketio.emit("rpa_agents_update", {"agent_ids": [agent_id]})


def _command_event(data, completed=False):
    data = data if isinstance(data, dict) else {}
    command_id = str(data.get("command_id") or "")
    agent_id = str(data.get("agent_id") or "")
    tracked = active_commands.get(command_id)
    registered = agents.get(agent_id)
    if not tracked or not registered or registered["sid"] != rq.sid:
        return
    tracked["agent_id"] = agent_id
    completed = completed or str(data.get("status") or "").strip().lower() == "completed"
    payload = {
        "command_id": command_id,
        "agent_id": agent_id,
        "capability": tracked["capability"],
        "progress": min(100, max(0, int(data.get("progress", 100 if completed else 0)))),
        "step": str(data.get("step") or "").strip()[:180],
        "status": str(data.get("status") or ("completed" if completed else "running"))[:30],
    }
    socketio.emit("rpa_progress", payload, to=f"user:{tracked['user_id']}")
    if completed:
        active_commands.pop(command_id, None)


@socketio.on("command_progress")
def on_command_progress(data):
    _command_event(data)


@socketio.on("command_done")
def on_command_done(data):
    _command_event(data, completed=True)
