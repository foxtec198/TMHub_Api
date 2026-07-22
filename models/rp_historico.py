from models.base_model import BaseModel
from datetime import datetime as dt
from utils.db import db

class History(BaseModel):
    __tablename__ = "rp_historico"

    id = db.Column(db.Integer, primary_key=True)
    requisicao_id = db.Column(db.Integer, nullable=False)
    reserva_id = db.Column(db.Integer, nullable=False)
    ausente_id = db.Column(db.Integer, nullable=False)
    cc = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=dt.now)
    supervisor_id = db.Column(db.Integer)
    ended_at = db.Column(db.DateTime)
    motivo = db.Column(db.String)
    obs = db.Column(db.String)
