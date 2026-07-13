from datetime import datetime as dt

from models.base_model import BaseModel
from utils.db import db


class Ponto48Import(BaseModel):
    __tablename__ = "pt48_importacoes"

    id = db.Column(db.Integer, primary_key=True)
    periodo_inicio = db.Column(db.Date, nullable=False, index=True)
    periodo_fim = db.Column(db.Date, nullable=False, index=True)
    arquivo_absenteismo = db.Column(db.String(255), nullable=False)
    arquivo_horas_extras = db.Column(db.String(255), nullable=False)
    criado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=dt.now)


class Ponto48Absenteismo(BaseModel):
    __tablename__ = "pt48_absenteismo"

    id = db.Column(db.Integer, primary_key=True)
    importacao_id = db.Column(
        db.Integer,
        db.ForeignKey("pt48_importacoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nome_colaborador = db.Column(db.String(255), nullable=False)
    nome_normalizado = db.Column(db.String(255), nullable=False, index=True)
    match_status = db.Column(db.String(20), nullable=False, default="unmatched")
    previsto_minutos = db.Column(db.Integer, nullable=False, default=0)
    ausencia_minutos = db.Column(db.Integer, nullable=False, default=0)
    presenca_minutos = db.Column(db.Integer, nullable=False, default=0)
    abs_percentual = db.Column(db.Numeric(7, 2), nullable=False, default=0)


class Ponto48HorasExtras(BaseModel):
    __tablename__ = "pt48_horas_extras"

    id = db.Column(db.Integer, primary_key=True)
    importacao_id = db.Column(
        db.Integer,
        db.ForeignKey("pt48_importacoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nome_colaborador = db.Column(db.String(255), nullable=False)
    nome_normalizado = db.Column(db.String(255), nullable=False, index=True)
    match_status = db.Column(db.String(20), nullable=False, default="unmatched")
    data = db.Column(db.Date, nullable=False, index=True)
    entrada_1 = db.Column(db.String(5))
    saida_1 = db.Column(db.String(5))
    entrada_2 = db.Column(db.String(5))
    saida_2 = db.Column(db.String(5))
    entrada_3 = db.Column(db.String(5))
    saida_3 = db.Column(db.String(5))
    horas_normais_minutos = db.Column(db.Integer, nullable=False, default=0)
    horas_extras_minutos = db.Column(db.Integer, nullable=False, default=0)
    motivo = db.Column(db.String(255))
    quantidade_batidas = db.Column(db.Integer, nullable=False, default=0)
    batida_impar = db.Column(db.Boolean, nullable=False, default=False)
    batida_irregular = db.Column(db.Boolean, nullable=False, default=False)
    irregularidade = db.Column(db.String(500))
