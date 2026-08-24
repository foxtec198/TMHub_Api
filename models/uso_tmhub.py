"""Telemetria operacional agregada do uso do TM Hub."""

from datetime import datetime as dt

from models.base_model import BaseModel
from utils.db import db


class TMHubUsageDaily(BaseModel):
    """Resumo diário por usuário; é a base para métricas e Edinhos."""

    __tablename__ = "tm_uso_diario"
    __table_args__ = (
        db.UniqueConstraint("usuario_id", "dia", name="uq_tm_uso_diario_usuario_dia"),
    )

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dia = db.Column(db.Date, nullable=False, index=True)
    primeira_atividade_em = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    ultima_atividade_em = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    segundos_ativos = db.Column(db.Integer, nullable=False, default=0)
    paginas_visitadas = db.Column(db.Integer, nullable=False, default=0)
    acoes_concluidas = db.Column(db.Integer, nullable=False, default=0)
    edinhos_gerados = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now, onupdate=dt.now)

    usuario = db.relationship("Users", backref=db.backref("uso_diario", lazy="dynamic"))


class TMHubUsageEvent(BaseModel):
    """Eventos legíveis da timeline, sem registrar conteúdo sensível."""

    __tablename__ = "tm_uso_eventos"
    __table_args__ = (
        db.Index("ix_tm_uso_eventos_diario_ocorrido", "uso_diario_id", "ocorrido_em"),
        db.Index("ix_tm_uso_eventos_usuario_ocorrido", "usuario_id", "ocorrido_em"),
    )

    id = db.Column(db.Integer, primary_key=True)
    uso_diario_id = db.Column(
        db.Integer,
        db.ForeignKey("tm_uso_diario.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo = db.Column(db.String(32), nullable=False, index=True)
    rota = db.Column(db.String(240), nullable=True)
    metodo = db.Column(db.String(12), nullable=True)
    ocorrido_em = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now, index=True)

    uso_diario = db.relationship("TMHubUsageDaily", backref=db.backref("eventos", lazy="dynamic"))
    usuario = db.relationship("Users", backref=db.backref("eventos_uso", lazy="dynamic"))


class TMHubEdinhoLedger(BaseModel):
    """Livro-caixa auditável; recompensas futuras podem debitar sem perder origem."""

    __tablename__ = "tm_edinho_lancamentos"
    __table_args__ = (
        db.UniqueConstraint("uso_diario_id", name="uq_tm_edinho_lancamentos_uso_diario"),
        db.Index("ix_tm_edinho_lancamentos_usuario", "usuario_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uso_diario_id = db.Column(
        db.Integer,
        db.ForeignKey("tm_uso_diario.id", ondelete="CASCADE"),
        nullable=True,
    )
    tipo = db.Column(db.String(32), nullable=False, default="uso_diario", index=True)
    quantidade = db.Column(db.Integer, nullable=False, default=0)
    descricao = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now, onupdate=dt.now)

    usuario = db.relationship("Users", backref=db.backref("edinho_lancamentos", lazy="dynamic"))
    uso_diario = db.relationship("TMHubUsageDaily", backref=db.backref("edinho_lancamento", uselist=False))
