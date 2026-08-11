from models.base_model import BaseModel
from utils.db import db
from datetime import datetime as dt

class Floaters(BaseModel):
    __tablename__ = "volantes"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=dt.now())
    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    was_used = db.Column(db.Integer, default=0)
    disponivel = db.Column(db.Boolean, nullable=False, default=True, index=True)
    indisponibilidade_motivo = db.Column(db.String(12))
    indisponivel_em = db.Column(db.DateTime)
