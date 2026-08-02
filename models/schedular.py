from datetime import datetime as dt

from models.base_model import BaseModel
from utils.db import db


class SchedularAccess(BaseModel):
    """Credencial independente do login administrativo do TMHub."""

    __tablename__ = "schedular_acessos"

    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(30), nullable=False, default="executor")
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    token_version = db.Column(db.Integer, nullable=False, default=0)
    senha_pendente = db.Column(db.Boolean, nullable=False, default=True)
    ultimo_login = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now, onupdate=dt.now)
