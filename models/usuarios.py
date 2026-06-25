from utils.db import db
from models.base_model import BaseModel
from datetime import datetime as dt

class Users(BaseModel):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String)
    email = db.Column(db.String)
    cpf = db.Column(db.String, unique=True, nullable=False)
    hash = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=dt.now())
    last_login = db.Column(db.DateTime)
    role = db.Column(db.String, default="USER")