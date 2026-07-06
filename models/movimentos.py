from utils.db import db
from models.base_model import BaseModel
from datetime import datetime as dt

class Movement(BaseModel):
    __tablename__ = "es_movimentos"

    id = db.Column(db.BigInteger, primary_key=True)
    item_id = db.Column(db.BigInteger, nullable=False)
    produto = db.Column(db.String(50))
    tipo = db.Column(db.String(20), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    data_hora = db.Column(db.DateTime, default=dt.now)
    observacao = db.Column(db.Text)
    origem = db.Column(db.String(50), default="desktop")