# Utilitários de tokens de acesso.
# Dependências externas.
from jwt import encode, decode
from dateutils import relativedelta
# Biblioteca padrão.
from os import getenv
from datetime import datetime

def create_token(dados:dict, expires=True):
    payload = dict(dados)
    if expires:
        payload["exp"] = datetime.now() + relativedelta(hours=8)
    token = str(encode(payload, getenv("SECRET"), algorithm="HS256"))
    return token

def decode_token(token:str) -> str | None:
    return decode(token, getenv("SECRET"), algorithms=["HS256"])
