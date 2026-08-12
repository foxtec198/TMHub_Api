"""Canal Socket.IO autenticado para o Timo Voice Agent."""

from datetime import datetime, timezone

from flask import request

from models.timo_voice_agents import TimoUserPreference, TimoVoiceAgent
from models.usuarios import Users
from services.timo_voice_agents import validate_agent_token
from utils.db import db
from utils.socket import socketio


_agent_sids = {}
_sid_agents = {}


def _now():
    return datetime.now(timezone.utc)


def _is_connected(sid):
    return bool(sid and socketio.server.manager.is_connected(sid, namespace="/"))


def is_agent_online(agent_id):
    sid = _agent_sids.get(str(agent_id))
    return _is_connected(sid)


def _emit_user_status(agent):
    socketio.emit(
        "timo_agent_status",
        {
            "id": agent.id,
            "online": is_agent_online(agent.id),
            "estado": agent.ultimo_estado or "desconectado",
            "ultimo_heartbeat_em": agent.ultimo_heartbeat_em.isoformat()
            if agent.ultimo_heartbeat_em else None,
        },
        to=f"user:{agent.usuario_id}",
    )


def _control_payload(agent, enabled):
    """Entrega ao agente o tema visual persistido do proprietário."""
    user = db.session.get(Users, agent.usuario_id)
    return {
        "habilitado": bool(enabled),
        "tema": (user.tema if user else None) or "tmhub",
        "modo_tema": (user.modo_tema if user else None) or "light",
    }


def register_agent_socket(token, sid):
    agent, _ = validate_agent_token(token)
    _agent_sids[agent.id] = sid
    _sid_agents[sid] = agent.id
    agent.ultimo_estado = agent.ultimo_estado or "aguardando_wake_word"
    agent.ultimo_heartbeat_em = _now()
    db.session.commit()
    _emit_user_status(agent)
    preference = db.session.get(TimoUserPreference, agent.usuario_id)
    socketio.emit(
        "timo_agent_control",
        _control_payload(
            agent,
            bool(preference and preference.habilitado and preference.agente_preferido_id == agent.id),
        ),
        to=sid,
    )
    return agent


def disconnect_agent(agent_id):
    sid = _agent_sids.pop(str(agent_id), None)
    if sid:
        _sid_agents.pop(sid, None)
        if _is_connected(sid):
            socketio.emit(
                "timo_agent_revoked",
                {"motivo": "Este agente foi revogado no TMHub."},
                to=sid,
            )
            socketio.server.disconnect(sid, namespace="/")


def unregister_agent_socket(sid):
    agent_id = _sid_agents.pop(sid, None)
    if not agent_id:
        return
    _agent_sids.pop(agent_id, None)
    agent = db.session.get(TimoVoiceAgent, agent_id)
    if agent:
        agent.ultimo_estado = "desconectado"
        agent.ultimo_heartbeat_em = _now()
        db.session.commit()
        _emit_user_status(agent)


def emit_agent_control(agent_id, enabled):
    agent = db.session.get(TimoVoiceAgent, agent_id)
    if not agent:
        return
    sid = _agent_sids.get(str(agent_id))
    if _is_connected(sid):
        socketio.emit("timo_agent_control", _control_payload(agent, enabled), to=sid)
    elif sid:
        unregister_agent_socket(sid)


def _current_agent():
    agent_id = _sid_agents.get(request.sid)
    return db.session.get(TimoVoiceAgent, agent_id) if agent_id else None


@socketio.on("timo_agent_heartbeat")
def agent_heartbeat(payload=None):
    agent = _current_agent()
    if not agent:
        return False
    state = str((payload or {}).get("estado") or "aguardando_wake_word")[:32]
    agent.ultimo_estado = state
    agent.ultimo_heartbeat_em = _now()
    db.session.commit()
    _emit_user_status(agent)
    return {"ok": True}


@socketio.on("timo_agent_ready")
def agent_ready():
    """Sincroniza o controle após o handshake do agente estar concluído."""
    agent = _current_agent()
    if not agent:
        return {"ok": False}
    preference = db.session.get(TimoUserPreference, agent.usuario_id)
    enabled = bool(
        preference
        and preference.habilitado
        and preference.agente_preferido_id == agent.id
    )
    socketio.emit("timo_agent_control", _control_payload(agent, enabled), to=request.sid)
    return {"ok": True, "habilitado": enabled}


@socketio.on("timo_agent_response")
def agent_response(payload=None):
    agent = _current_agent()
    result = (payload or {}).get("resultado")
    if not agent or not isinstance(result, dict):
        return {"ok": False}
    socketio.emit(
        "timo_agent_response",
        {"agent_id": agent.id, **result},
        to=f"user:{agent.usuario_id}",
    )
    return {"ok": True}
