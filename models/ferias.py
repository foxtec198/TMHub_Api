# Biblioteca padrão.
from datetime import datetime as dt

# Módulos internos da aplicação.
from models.base_model import BaseModel
from utils.db import db


class VacationPeriod(BaseModel):
    """Representa um período aquisitivo de férias de um colaborador."""

    __tablename__ = "rh_ferias_periodos"
    __table_args__ = (
        db.UniqueConstraint(
            "colaborador_id",
            "periodo_aquisitivo_inicio",
            name="uq_rh_ferias_periodos_colaborador_inicio",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    periodo_aquisitivo_inicio = db.Column(db.Date, nullable=False, index=True)
    periodo_aquisitivo_fim = db.Column(db.Date, nullable=False)
    limite_concessivo = db.Column(db.Date, nullable=False, index=True)
    dias_direito = db.Column(db.Integer, nullable=False, default=30)
    pagamento_ferias_integral = db.Column(db.Boolean, nullable=False, default=True)
    va_ferias_integral_pago = db.Column(db.Boolean, nullable=False, default=True)
    valor_ferias = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    valor_terco_ferias = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    valor_complementar = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    valor_descontos = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    valor_liquido = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    arquivo_origem = db.Column(db.String(255))
    observacao_manual = db.Column(db.String(1000))
    ajustado_manual = db.Column(db.Boolean, nullable=False, default=False)
    ajustado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        index=True,
    )
    ajustado_em = db.Column(db.DateTime(timezone=True))
    importado_por_usuario_id = db.Column(
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

    colaborador = db.relationship("Employees")
    gozos = db.relationship(
        "VacationLeave",
        cascade="all, delete-orphan",
        passive_deletes=True,
        back_populates="periodo",
        order_by="VacationLeave.data_inicio",
    )


class VacationLeave(BaseModel):
    """Registra cada fração efetivamente gozada dentro de um período."""

    __tablename__ = "rh_ferias_gozos"

    id = db.Column(db.Integer, primary_key=True)
    periodo_id = db.Column(
        db.Integer,
        db.ForeignKey("rh_ferias_periodos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_inicio = db.Column(db.Date, nullable=False, index=True)
    data_fim = db.Column(db.Date, nullable=False)
    dias_gozados = db.Column(db.Integer, nullable=False)
    dias_calculados_pagos = db.Column(db.Integer, nullable=False, default=0)
    pagamento_realizado = db.Column(db.Boolean, nullable=False, default=False)
    observacao = db.Column(db.String(1000))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=dt.now,
        onupdate=dt.now,
    )

    periodo = db.relationship("VacationPeriod", back_populates="gozos")
