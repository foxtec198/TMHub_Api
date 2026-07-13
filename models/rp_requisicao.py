from models.base_model import BaseModel
from datetime import datetime as dt
from utils.db import db

class Requisicao(BaseModel):
    __tablename__ = "rp_requisicoes"

    id = db.Column(db.Integer, primary_key=True)
    reserva_id = db.Column(db.Integer, nullable=False)
    ausente_id = db.Column(db.Integer, nullable=False)
    cc = db.Column(db.Integer, nullable=True)
    supervisor_id = db.Column(db.Integer, nullable=False)
    warning = db.Column(db.Boolean, default=False)
    motivo = db.Column(db.String)
    obs = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=dt.now())
    # Persist the calculated absence range so daily availability queries remain deterministic.
    end_at = db.Column(db.DateTime)
    quantidade_dias = db.Column(db.Integer, default=1)
    status = db.Column(db.String, default="pending")
