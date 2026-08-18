from utils.db import db
from models.base_model import BaseModel


class QLDailySnapshot(BaseModel):
    """Fotografia diária do quadro de lotação por filial e departamento."""

    __tablename__ = "ql_historico_diario"
    __table_args__ = (
        db.UniqueConstraint(
            "data_referencia",
            "filial_id",
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
