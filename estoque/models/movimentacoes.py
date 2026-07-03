from utils.db import db
from models.base_model import BaseModel
from datetime import datetime as dt

class Movements(BaseModel):
    __tablename__ = "es_movimentos"

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.String, nullable=False)   # "ENTRADA" ou "SAIDA"
    quantidade = db.Column(db.Integer, nullable=False)
    sup = db.Column(db.String)                    # supervisor/responsável pela movimentação
    local_destino = db.Column(db.String, nullable=True)               # local de destino da movimentação
    data = db.Column(db.DateTime, default=dt.now)