# Modelo de dados de categorias.
# Módulos internos da aplicação.
from utils.db import db
from models.base_model import BaseModel

# Define a entidade Category persistida no banco de dados.
class Category(BaseModel):
    __tablename__ = "es_categorias"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String)
    descricao = db.Column(db.String)
