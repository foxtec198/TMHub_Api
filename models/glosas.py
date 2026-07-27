from datetime import datetime as dt
from decimal import Decimal

from models.base_model import BaseModel
from utils.db import db


class Disallowance(BaseModel):
    __tablename__ = "controle_glosas"

    id = db.Column(db.Integer, primary_key=True)
    competencia = db.Column(db.Date, nullable=False, index=True)
    data_falta = db.Column(db.Date, nullable=False, index=True)
    centro_custo_id = db.Column(
        db.Integer,
        db.ForeignKey("centro_de_custo.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="SET NULL"),
        index=True,
    )
    colaborador_nome = db.Column(db.String(255))
    colaborador_matricula = db.Column(db.String(50))
    falta_id = db.Column(
        db.Integer,
        db.ForeignKey("controle_faltas.id", ondelete="SET NULL"),
        index=True,
    )
    requisicao_id = db.Column(
        db.Integer,
        db.ForeignKey("rp_requisicoes.id", ondelete="SET NULL"),
        index=True,
    )
    cobertura = db.Column(db.String(20), nullable=False, default="em_analise", index=True)
    quantidade_dias = db.Column(db.Numeric(8, 4), nullable=False, default=Decimal("1.0000"))
    quantidade_coberta_dias = db.Column(db.Numeric(8, 4), nullable=False, default=Decimal("0.0000"))
    valor_diaria = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("180.00"))
    valor_total = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("180.00"))
    valor_coberto = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    valor_descoberto = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("180.00"))
    evidencia_arquivo = db.Column(db.String(255))
    evidencia_nome_original = db.Column(db.String(255))
    evidencia_mime = db.Column(db.String(120))
    justificativa = db.Column(db.Text)
    observacao = db.Column(db.Text)
    criado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        index=True,
    )
    alterado_por_usuario_id = db.Column(
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
