# Modelo de dados de configurações do Timo.
# Biblioteca padrão.
from datetime import datetime as dt

# Módulos internos da aplicação.
from models.base_model import BaseModel
from utils.db import db


# Define a entidade TimoIntentConfiguration persistida no banco de dados.
class TimoIntentConfiguration(BaseModel):
    """Resposta visual e ação permitida para cada intenção reconhecida pelo Timo."""

    __tablename__ = "timo_configuracoes"

    id = db.Column(db.Integer, primary_key=True)
    intent = db.Column(db.String(100), nullable=False, unique=True, index=True)
    titulo = db.Column(db.String(150), nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    personalizado = db.Column(db.Boolean, nullable=False, default=False, index=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    resposta_template = db.Column(db.Text, nullable=True)
    acao_tipo = db.Column(db.String(30), nullable=False, default="none")
    acao_valor = db.Column(db.String(255), nullable=True)
    atualizado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        index=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=dt.now,
        onupdate=dt.now,
    )


# Define a entidade TimoCommandTrigger persistida no banco de dados.
class TimoCommandTrigger(BaseModel):
    """Frase de ativação cadastrada para uma automação personalizada."""

    __tablename__ = "timo_comandos"

    id = db.Column(db.Integer, primary_key=True)
    configuracao_id = db.Column(
        db.Integer,
        db.ForeignKey("timo_configuracoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    frase = db.Column(db.String(500), nullable=False)
    frase_normalizada = db.Column(db.String(500), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)

    configuracao = db.relationship(
        "TimoIntentConfiguration",
        backref=db.backref("comandos", cascade="all, delete-orphan", lazy="selectin"),
    )
