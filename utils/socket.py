# Utilitários de eventos Socket.IO.
# Dependências externas.
from flask import request
from flask_socketio import SocketIO, join_room

# Módulos internos da aplicação.
from utils.token import decode_token
from models.usuarios import Users
from utils.db import db
from utils.user_requirements import auth_requirements

socketio = SocketIO()


@socketio.on("connect")
def register_authenticated_client(auth=None):
    """Keep browser clients in a stable user room across socket reconnects."""
    agent_token = (auth or {}).get("agent_token")
    if agent_token:
        try:
            # Import local evita ciclo entre o Socket.IO e o serviço de agentes.
            from utils.timo_voice_socket import register_agent_socket
            register_agent_socket(agent_token, request.sid)
            return True
        except Exception:
            return False
    token = (auth or {}).get("token")
    if not token:
        return
    try:
        token_data = decode_token(token)
        user_id = token_data.get("id")
        user = db.session.get(Users, user_id)
        if not user or int(token_data.get("ver", 0)) != int(user.token_version or 0):
            return False
        if auth_requirements(user)["interacao_pendente"]:
            return False
        join_room(f"user:{user_id}")
    except Exception:
        # RPA agents share this namespace and authenticate through "register".
        return


@socketio.on("disconnect")
def unregister_socket_client():
    """Mantém todas as tabelas de sessão sincronizadas ao fechar uma conexão."""
    try:
        from utils.timo_voice_socket import unregister_agent_socket
        unregister_agent_socket(request.sid)
    except Exception:
        pass
    try:
        from routes.rpa import unregister_rpa_agent
        unregister_rpa_agent(request.sid)
    except Exception:
        pass
