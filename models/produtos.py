from utils.db import db
from models.base_model import BaseModel
from datetime import datetime as dt

class Product(BaseModel):
    __tablename__ = "es_produtos"

    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer)
    nome = db.Column(db.String)
    unidade = db.Column(db.String)
    quantidade = db.Column(db.Integer, default=0)
    quantidade_minima = db.Column(db.Integer, default=0)
    local_estoque = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=dt.now)