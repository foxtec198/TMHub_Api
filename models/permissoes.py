from datetime import datetime as dt

from models.base_model import BaseModel
from utils.db import db


class UserPermission(BaseModel):
    __tablename__ = "usuario_permissoes"
    __table_args__ = (
        db.UniqueConstraint("usuario_id", "tela", name="uq_usuario_permissoes_usuario_tela"),
    )

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tela = db.Column(db.String(80), nullable=False, index=True)
    pode_ver = db.Column(db.Boolean, nullable=False, default=False)
    pode_criar = db.Column(db.Boolean, nullable=False, default=False)
    pode_alterar = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=dt.now,
        onupdate=dt.now,
    )
