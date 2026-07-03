from utils.db import db
from models.base_model import BaseModel
from datetime import datetime as dt

class Products(BaseModel):
    __tablename__ = "es_produtos"

    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer)
    unidade = db.Column(db.String) # tipos de unidade
    quantidade = db.Column(db.Integer, default=0) # estoque atual
    quantidade_minima = db.Column(db.Integer, default=0) # ponto de alerta de reposição
    local_estoque = db.Column(db.String) #local físico no estoque
    created_at = db.Column(db.DateTime, default=dt.now) #registra quando foi criado o produto
