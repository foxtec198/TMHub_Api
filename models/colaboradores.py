from utils.db import db
from models.base_model import BaseModel
from datetime import datetime as dt

class Employees(BaseModel):
    __tablename__ = "colaboradores"

    id = db.Column(db.Integer, primary_key=True)
    matricula = db.Column(db.String, nullable=False)
    nome = db.Column(db.String)
    centro_id = db.Column(db.Integer)
    data_admissao = db.Column(db.DateTime, default=dt.now())
    cargo = db.Column(db.Integer)
    situacao = db.Column(db.Integer)