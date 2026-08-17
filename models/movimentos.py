# Modelo de dados de movimentações de estoque.
# Módulos internos da aplicação.
from utils.db import db
from models.base_model import BaseModel
# Biblioteca padrão.
from datetime import datetime as dt

# Define a entidade Movement persistida no banco de dados.
class Movement(BaseModel):
    __tablename__ = "es_movimentos"

    id = db.Column(db.BigInteger, primary_key=True)
    item_id = db.Column(db.BigInteger, nullable=False)
    produto = db.Column(db.String(50))
    tipo = db.Column(db.String(20), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    data_hora = db.Column(db.DateTime, default=dt.now)
    observacao = db.Column(db.Text)
    origem = db.Column(db.String(50), default="desktop")
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    destinatarios = db.relationship(
        "MovementRecipient",
        back_populates="movimentacao",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# Define a entidade MovementRecipient persistida no banco de dados.
class MovementRecipient(BaseModel):
    __tablename__ = "es_movimento_destinatarios"
    __table_args__ = (
        db.UniqueConstraint(
            "movimentacao_id",
            "colaborador_id",
            name="uq_es_mov_dest_mov_colaborador",
        ),
        db.CheckConstraint("quantidade > 0", name="ck_es_mov_dest_quantidade_positiva"),
        db.Index("ix_es_mov_dest_colaborador_data", "colaborador_id", "created_at"),
        db.Index("ix_es_mov_dest_centro_data", "centro_custo_id", "created_at"),
    )

    id = db.Column(db.BigInteger, primary_key=True)
    movimentacao_id = db.Column(
        db.BigInteger,
        db.ForeignKey("es_movimentos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    centro_custo_id = db.Column(
        db.Integer,
        db.ForeignKey("centro_de_custo.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantidade = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=dt.now)

    movimentacao = db.relationship("Movement", back_populates="destinatarios")
