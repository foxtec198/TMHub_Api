from models.base_model import BaseModel
from utils.db import db

class Cities(BaseModel):
    __tablename__ = "cidades"

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String)