import sys
from pathlib import Path

from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app
from utils.db import db


with app.app_context():
    columns = {column["name"] for column in inspect(db.engine).get_columns("usuarios")}
    if "tema" not in columns:
        with db.engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE usuarios ADD COLUMN tema VARCHAR(10) DEFAULT 'light'"
            ))
        print("Coluna usuarios.tema criada.")
    else:
        print("Coluna usuarios.tema ja existe.")
