from utils.db import db
from models.base_model import BaseModel


class QLDepartmentCapacity(BaseModel):
    """Meta contratual do QL isolada por empresa e departamento."""

    __tablename__ = "ql_capacidades_empresa"

    empresa_id = db.Column(
        db.Integer,
        db.ForeignKey("empresas.id", ondelete="CASCADE"),
        primary_key=True,
    )
    departamento = db.Column(db.Integer, primary_key=True)
    capacidade_esperada = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )


class QLDailySnapshot(BaseModel):
    """Fotografia diária do quadro de lotação por filial e departamento."""

    # A tabela anterior consolidava empresas que compartilhavam o mesmo DPTO.
    # A nova tabela preserva a identidade composta empresa + departamento.
    __tablename__ = "ql_historico_empresa_diario"
    __table_args__ = (
        db.UniqueConstraint(
            "data_referencia",
            "filial_id",
            "empresa_id",
            "departamento",
            name="uq_ql_historico_diario_escopo",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    data_referencia = db.Column(db.Date, nullable=False, index=True)
    filial_id = db.Column(
        db.Integer,
        db.ForeignKey("filiais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    empresa_id = db.Column(
        db.Integer,
        db.ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    departamento = db.Column(db.Integer, nullable=False, index=True)
    colaboradores_ativos = db.Column(db.Integer, nullable=False, default=0)
    capacidade_esperada = db.Column(db.Integer, nullable=True)
    centros_quantidade = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    filial = db.relationship("Branch", foreign_keys=[filial_id])
