from datetime import datetime as dt
from uuid import uuid4

from models.base_model import BaseModel
from utils.db import db


class TimoVoiceAgent(BaseModel):
    """Dispositivo desktop pareado, com credencial exclusiva para o Timo."""

    __tablename__ = "timo_voice_agents"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dispositivo_id = db.Column(db.String(128), nullable=False, unique=True, index=True)
    nome = db.Column(db.String(120), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    token_version = db.Column(db.Integer, nullable=False, default=0)
    ultimo_heartbeat_em = db.Column(db.DateTime(timezone=True), nullable=True)
    ultimo_estado = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=dt.now, onupdate=dt.now
    )


class TimoVoicePairing(BaseModel):
    """Código efêmero de uso único. O código puro jamais é persistido."""

    __tablename__ = "timo_voice_pairings"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    codigo_hash = db.Column(db.String(128), nullable=False, unique=True, index=True)
    expira_em = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    utilizado_em = db.Column(db.DateTime(timezone=True), nullable=True)
    agente_id = db.Column(
        db.String(36),
        db.ForeignKey("timo_voice_agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)


class TimoUserPreference(BaseModel):
    """Preferências sincronizadas por conta, independentes do computador."""

    __tablename__ = "timo_preferencias_usuario"

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    agente_preferido_id = db.Column(
        db.String(36),
        db.ForeignKey("timo_voice_agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    habilitado = db.Column(db.Boolean, nullable=False, default=False)
    skin = db.Column(db.String(80), nullable=True)
    tema_balao = db.Column(db.String(80), nullable=True)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=dt.now, onupdate=dt.now
    )
