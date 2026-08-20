"""Configurações globais e auditáveis da operação."""

from datetime import datetime as dt

from utils.db import db


class SystemConfiguration(db.Model):
    __tablename__ = "configuracoes_sistema"

    id = db.Column(db.Integer, primary_key=True)
    manutencao_ativa = db.Column(db.Boolean, nullable=False, default=False)
    atualizado_em = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now, onupdate=dt.now)
    atualizado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
