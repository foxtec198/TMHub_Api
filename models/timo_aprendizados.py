# Modelo de dados de aprendizados do Timo.
# Biblioteca padrão.
from datetime import datetime as dt

# Módulos internos da aplicação.
from models.base_model import BaseModel
from utils.db import db


# Define a entidade TimoLearningExample persistida no banco de dados.
class TimoLearningExample(BaseModel):
    """Frases sem entendimento que aguardam revisão humana antes do treino."""

    __tablename__ = "timo_aprendizados"

    id = db.Column(db.Integer, primary_key=True)
    texto_normalizado = db.Column(db.String(500), nullable=False, index=True)
    intent_sugerida = db.Column(db.String(100), nullable=True)
    confianca = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pendente", index=True)
    intent_confirmada = db.Column(db.String(100), nullable=True, index=True)
    ocorrencias = db.Column(db.Integer, nullable=False, default=1)
    criado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    revisado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=dt.now, onupdate=dt.now
    )
    revisado_em = db.Column(db.DateTime(timezone=True), nullable=True)
    ultimo_recebido_em = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
