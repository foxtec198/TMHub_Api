from models.base_model import BaseModel
from datetime import datetime as dt
from utils.db import db

class Reposicoes(BaseModel):
    __tablename__ = "reposicoes"

    id = db.Column(db.Integer, primary_key=True)
    requisicao_id = db.Column(db.String, nullable=False)
    reserva_id = db.Column(db.String, nullable=False)
    request_id = db.Column(db.Integer)
    cc = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=dt.now())
    ended_at = db.Column(db.DateTime)
    
class Requisicao(BaseModel):
    __tablename__ = "rp_requisicoes"

    id = db.Column(db.Integer, primary_key=True)
    reserva_id = db.Column(db.Integer, nullable=False)
    ausente_id = db.Column(db.Integer, nullable=False)
    cc = db.Column(db.Integer, nullable=True)
    supervisor_id = db.Column(db.Integer, nullable=False)
    warning = db.Column(db.Boolean, default=False)
    waiting_certificate = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=dt.now())
