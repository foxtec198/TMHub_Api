"""Catalogo e compras do marketplace interno."""
from datetime import datetime as dt

from models.base_model import BaseModel
from utils.db import db


class MarketplaceProduct(BaseModel):
    __tablename__ = "marketplace_produtos"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(80), nullable=False, unique=True, index=True)
    nome = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.String(500), nullable=True)
    categoria = db.Column(db.String(40), nullable=False, default="tema")
    preco_edinhos = db.Column(db.Integer, nullable=False, default=0)
    destaque = db.Column(db.Boolean, nullable=False, default=False)
    reembolsavel = db.Column(db.Boolean, nullable=False, default=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)


class MarketplacePurchase(BaseModel):
    __tablename__ = "marketplace_compras"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("marketplace_produtos.id", ondelete="RESTRICT"), nullable=False, index=True)
    preco_edinhos = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="concluida")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now, index=True)
    refunded_at = db.Column(db.DateTime(timezone=True), nullable=True)

    usuario = db.relationship("Users")
    produto = db.relationship("MarketplaceProduct")
