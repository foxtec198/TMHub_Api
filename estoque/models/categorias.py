

from models.base_model import BaseModel
from utils.db import db


class Categories(BaseModel):
    __tablename__ = "es_categorias"

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String)