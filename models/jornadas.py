from datetime import datetime as dt

from models.base_model import BaseModel
from utils.db import db


class JourneyImport(BaseModel):
    __tablename__ = "jornadas_importacoes"

    id = db.Column(db.Integer, primary_key=True)
    data_referencia = db.Column(db.Date, nullable=False, unique=True)
    arquivo_origem = db.Column(db.String(255), nullable=False)
    importado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    importado_em = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)


class JourneyOffense(BaseModel):
    __tablename__ = "jornadas_infracoes"

    id = db.Column(db.Integer, primary_key=True)
    importacao_id = db.Column(
        db.Integer,
        db.ForeignKey("jornadas_importacoes.id", ondelete="CASCADE"),
        nullable=False,
    )
    # O identificador é definido somente pela matrícula do relatório ou pelo
    # vínculo manual; o nome é uma informação descritiva da origem.
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nome_colaborador = db.Column(db.String(255), nullable=False)
    matricula = db.Column(db.String(30), index=True)
    data_ocorrencia = db.Column(db.Date, nullable=False, index=True)
    indicador = db.Column(db.String(20), nullable=False, index=True)
    resultado_relatorio = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)

    __table_args__ = (
        db.UniqueConstraint(
            "importacao_id",
            "matricula",
            "data_ocorrencia",
            "indicador",
            name="uq_jornadas_infracao_importacao",
        ),
    )
