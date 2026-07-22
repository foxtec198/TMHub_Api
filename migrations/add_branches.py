import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app
from utils.db import db


with app.app_context():
    # db.create_all() (executed by app.py) creates the new tables. This
    # migration only performs the compatibility backfill for existing data.
    with db.engine.begin() as connection:
        branch_id = connection.execute(text("SELECT id FROM filiais ORDER BY id LIMIT 1")).scalar()
        if branch_id is None:
            branch_id = connection.execute(text(
                "INSERT INTO filiais (nome, ativa, created_at) VALUES ('Matriz', TRUE, CURRENT_TIMESTAMP) RETURNING id"
            )).scalar_one()
        connection.execute(text("""
            INSERT INTO filial_usuarios (filial_id, usuario_id)
            SELECT :branch_id, usuario.id FROM usuarios AS usuario
            ON CONFLICT (filial_id, usuario_id) DO NOTHING
        """), {"branch_id": branch_id})
        connection.execute(text("""
            INSERT INTO filial_centros_custo (filial_id, centro_custo_id)
            SELECT :branch_id, centro.id FROM centro_de_custo AS centro
            ON CONFLICT (filial_id, centro_custo_id) DO NOTHING
        """), {"branch_id": branch_id})
    print("Filiais criadas; usuários e contratos existentes vinculados à filial padrão.")
