# Utilitários de tokens de acesso.
# Dependências externas.
from jwt import encode, decode
from dateutils import relativedelta
# Biblioteca padrão.
from os import getenv
from datetime import datetime, timedelta, timezone

def create_token(dados:dict, expires=True, expires_in_minutes=None):
    payload = dict(dados)
    if expires:
        now = datetime.now(timezone.utc)
        payload["exp"] = (
            now + timedelta(minutes=expires_in_minutes)
            if expires_in_minutes is not None
            else now + relativedelta(hours=8)
        )
    token = str(encode(payload, getenv("SECRET"), algorithm="HS256"))
    return token

def decode_token(token:str) -> str | None:
    return decode(token, getenv("SECRET"), algorithms=["HS256"])
