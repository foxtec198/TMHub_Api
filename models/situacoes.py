from models.base_model import BaseModel
from utils.db import db

class Situations(BaseModel):
    __tablename__ = "situacoes"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String)