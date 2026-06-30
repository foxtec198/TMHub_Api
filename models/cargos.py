from models.base_model import BaseModel
from utils.db import db


class Cargos(BaseModel):
    __tablename__ = "cargos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String)
    multa = db.Column(db.Float)
    active = db.Column(db.Bool)