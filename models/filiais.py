from datetime import datetime as dt

from models.base_model import BaseModel
from utils.db import db


filial_usuarios = db.Table(
    "filial_usuarios",
    db.Column("filial_id", db.Integer, db.ForeignKey("filiais.id", ondelete="CASCADE"), primary_key=True),
    db.Column("usuario_id", db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
)

filial_centros_custo = db.Table(
    "filial_centros_custo",
    db.Column("filial_id", db.Integer, db.ForeignKey("filiais.id", ondelete="CASCADE"), primary_key=True),
    db.Column("centro_custo_id", db.Integer, db.ForeignKey("centro_de_custo.id", ondelete="CASCADE"), primary_key=True),
)

filial_departamentos = db.Table(
    "filial_departamentos",
    db.Column("filial_id", db.Integer, db.ForeignKey("filiais.id", ondelete="CASCADE"), primary_key=True),
    db.Column("departamento", db.Integer, primary_key=True),
)


class Branch(BaseModel):
    __tablename__ = "filiais"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    ativa = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=dt.now)

    usuarios = db.relationship("Users", secondary=filial_usuarios, back_populates="filiais")
    centros_custo = db.relationship("CostCenters", secondary=filial_centros_custo, back_populates="filiais")
