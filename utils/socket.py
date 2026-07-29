from flask_socketio import SocketIO, join_room

from utils.token import decode_token

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
        if user_id is not None:
            join_room(f"user:{user_id}")
    except Exception:
        # RPA agents share this namespace and authenticate through "register".
        return
