from datetime import datetime as dt

from models.base_model import BaseModel
from utils.db import db


class StructureAssetMovement(BaseModel):
    __tablename__ = "estrutura_ativo_movimentacoes"
    __table_args__ = (
        db.CheckConstraint(
            "tipo IN ('carga_inicial', 'transferencia')",
            name="ck_estrutura_ativo_mov_tipo",
        ),
        db.Index(
            "ix_estrutura_ativo_mov_ativo_data",
            "ativo_id",
            "data_hora",
        ),
        db.Index(
            "ix_estrutura_ativo_mov_origem_data",
            "centro_custo_origem_id",
            "data_hora",
        ),
        db.Index(
            "ix_estrutura_ativo_mov_destino_data",
            "centro_custo_destino_id",
            "data_hora",
        ),
        db.Index(
            "uq_estrutura_ativo_mov_carga_inicial",
            "ativo_id",
            unique=True,
            postgresql_where=db.text("tipo = 'carga_inicial'"),
        ),
    )

    id = db.Column(db.BigInteger, primary_key=True)
    ativo_id = db.Column(
        db.Integer,
        db.ForeignKey("estrutura_ativos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tipo = db.Column(db.String(20), nullable=False, default="transferencia")
    centro_custo_origem_id = db.Column(
        db.Integer,
        db.ForeignKey("centro_de_custo.id", ondelete="RESTRICT"),
        nullable=True,
    )
    centro_custo_destino_id = db.Column(
        db.Integer,
        db.ForeignKey("centro_de_custo.id", ondelete="RESTRICT"),
        nullable=False,
    )
    local_origem_id = db.Column(
        db.Integer,
        db.ForeignKey("estrutura_locais.id", ondelete="SET NULL"),
        nullable=True,
    )
    local_destino_id = db.Column(
        db.Integer,
        db.ForeignKey("estrutura_locais.id", ondelete="SET NULL"),
        nullable=True,
    )
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    data_hora = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=dt.now,
        server_default=db.func.now(),
    )
    observacao = db.Column(db.Text)

