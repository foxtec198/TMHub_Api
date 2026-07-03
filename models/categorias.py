from utils.db import db
from models.base_model import BaseModel

class Category(BaseModel):
    __tablename__ = "es_categorias"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String)
    descricao = db.Column(db.String)