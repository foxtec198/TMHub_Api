# =============================== Utils
from utils.db import db
from datetime import datetime as dt

# =============================== Models
from models.base_model import BaseModel


# Define os setores organizacionais
class Sector(BaseModel):
    __tablename__ = "setores"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
