import sys
from datetime import datetime as dt, timedelta
from pathlib import Path

from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app
from utils.db import db


with app.app_context():
    columns = {column["name"] for column in inspect(db.engine).get_columns("rp_requisicoes")}
    if "opened_at" not in columns:
        with db.engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE rp_requisicoes ADD COLUMN opened_at TIMESTAMP WITH TIME ZONE NULL"
            ))

            now = dt.now()
            rows = connection.execute(text(
                "SELECT id, created_at FROM rp_requisicoes WHERE opened_at IS NULL"
            )).mappings()

            for row in rows:
                scheduled_at = row["created_at"] or now
                row_now = dt.now(scheduled_at.tzinfo) if scheduled_at.tzinfo else now
                opened_at = scheduled_at
                if scheduled_at.date() > row_now.date():
                    opened_at = scheduled_at.replace(
                        year=row_now.year,
                        month=row_now.month,
                        day=row_now.day,
                    )
                    if opened_at > row_now:
                        opened_at -= timedelta(days=1)

                connection.execute(text(
                    "UPDATE rp_requisicoes SET opened_at = :opened_at WHERE id = :id"
                ), {"opened_at": opened_at, "id": row["id"]})

        print("Coluna rp_requisicoes.opened_at criada e preenchida.")
    else:
        print("Coluna rp_requisicoes.opened_at ja existe.")
