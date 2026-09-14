from os import getenv
from flask import request
from flask_limiter import Limiter

# Função responsavel por gerar um id usando username
def get_rate_limit_key():
    user_id = request.get_json(silent=True).get("username")
    return f"user:{user_id}"

limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri=getenv("RATELIMIT_STORAGE_URI", "memory://"),
    default_limits=[],
)