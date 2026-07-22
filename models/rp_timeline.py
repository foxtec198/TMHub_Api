from models.base_model import BaseModel
from datetime import datetime as dt
from utils.db import db

class Timeline(BaseModel):
    __tablename__ = "rp_timeline"

    id = db.Column(db.Integer, primary_key=True)
    requisicao_id = db.Column(db.Integer, nullable=False)
    reserva_id = db.Column(db.Integer, nullable=False)
    ausente_id = db.Column(db.Integer, nullable=False)
    cc = db.Column(db.Integer, nullable=False)
    supervisor_id = db.Column(db.Integer, nullable=False)
    criado_por_supervisor_id = db.Column(db.Integer, nullable=True)
    alterado_por_usuario_id = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String, nullable=False)
    tipo = db.Column(db.String, nullable=False)
    motivo = db.Column(db.String)
    obs = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=dt.now)
