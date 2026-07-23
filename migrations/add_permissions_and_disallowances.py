import sys
from pathlib import Path

from sqlalchemy import inspect

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app
from models.glosas import Disallowance
from models.permissoes import UserPermission
from utils.db import db


with app.app_context():
    db.create_all()
    inspector = inspect(db.engine)
    required = {UserPermission.__tablename__, Disallowance.__tablename__}
    existing = set(inspector.get_table_names())
    missing = required - existing
    if missing:
        raise RuntimeError(f"Não foi possível criar: {', '.join(sorted(missing))}")
    print("Permissões por tela/ação e Controle de Glosas preparados.")
