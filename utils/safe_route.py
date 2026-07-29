import inspect
from functools import wraps

from flask import jsonify, request as rq
from jwt import ExpiredSignatureError

from utils.socket import socketio
from utils.token import decode_token


MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _response_status(result):
    if isinstance(result, tuple) and len(result) > 1 and isinstance(result[1], int):
        return result[1]
    return getattr(result, "status_code", 200)


def _should_emit_data_change(path):
    # The import endpoint emits only after the background transaction finishes.
    # Uploading each chunk must not refresh every connected screen.
    return not path.startswith("/importacao-colaboradores")


def _emit_data_change(token_data):
    try:
        socketio.emit(
            "data_changed",
            {
                "path": rq.path,
                "method": rq.method,
                "resource": rq.path.strip("/").split("/", 1)[0] or "root",
                "source_socket": rq.headers.get("X-TMHub-Socket-Id"),
                "user_id": token_data.get("id"),
            },
        )
    except Exception:
        # Realtime is complementary: a socket failure must never roll back or
        # report failure for a mutation that was already committed.
        return


def safe_route(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        access_token = rq.headers.get("Access-Token")
        if not access_token:
            return jsonify("Token de acesso obrigatorio"), 400
        try:
            token_data = decode_token(access_token)
            signature = inspect.signature(func)
            if "token_data" in signature.parameters:
                kwargs["token_data"] = token_data

            result = func(*args, **kwargs)
            if (
                rq.method in MUTATION_METHODS
                and _response_status(result) < 400
                and _should_emit_data_change(rq.path)
            ):
                _emit_data_change(token_data)
            return result
        except ExpiredSignatureError:
            return jsonify("Token de acesso expirado"), 401
        except Exception as error:
            return jsonify("Erro com o servidor: " + str(error)), 500

    return wrapper
