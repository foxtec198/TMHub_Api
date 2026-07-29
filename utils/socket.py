from flask_socketio import SocketIO, join_room

from utils.token import decode_token
from models.usuarios import Users
from utils.db import db
from utils.user_requirements import auth_requirements

socketio = SocketIO()


@socketio.on("connect")
def register_authenticated_client(auth=None):
    """Keep browser clients in a stable user room across socket reconnects."""
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
