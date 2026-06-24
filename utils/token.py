from jwt import encode, decode
from dateutils import relativedelta
from os import getenv
from datetime import datetime

def create_token(dados:dict):
    dados["exp"] = datetime.now() + relativedelta(hours=8)
    token = str(encode(dados, getenv("SECRET"), algorithm="HS256"))
    return token

def decode_token(token:str) -> str | None:
    return decode(token, getenv("SECRET"), algorithms=["HS256"])