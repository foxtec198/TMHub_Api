from os import getenv
from sqlalchemy import create_engine, text
from funcs import df

for item in df:
    with create_engine(getenv("DB_URI")).connect() as conn:
        func_id = conn.execute(text(f"SELECT id, from colaborador where matricula = {item.get("codigo")}")).first()
        func_id = func_id[0] if func_id else None