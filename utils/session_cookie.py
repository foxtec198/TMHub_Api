"""Sessão HTTP do navegador, mantida fora do alcance do JavaScript."""
from os import getenv

from flask import request


SESSION_COOKIE_NAME = "tmhub_session"


def request_access_token():
    """Aceita integrações legadas por header e o navegador por cookie HttpOnly."""
    return request.headers.get("Access-Token") or request.cookies.get(SESSION_COOKIE_NAME)


def _use_secure_cookie():
    configured = getenv("AUTH_COOKIE_SECURE")
    if configured is not None:
        return configured.strip().lower() in {"1", "true", "yes"}
    host = (request.host or "").split(":", 1)[0].lower()
    return host not in {"localhost", "127.0.0.1", "::1"}


def set_session_cookie(response, token, persistent=False):
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=60 * 60 * 24 * 30 if persistent else None,
        httponly=True,
        secure=_use_secure_cookie(),
        samesite="Lax",
        path="/",
    )
    return response


def clear_session_cookie(response):
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
        secure=_use_secure_cookie(),
        samesite="Lax",
    )
    return response
