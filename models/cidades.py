# Modelo de dados de cidades.
# Módulos internos da aplicação.
from models.base_model import BaseModel
from utils.db import db

# Define a entidade Cities persistida no banco de dados.
class Cities(BaseModel):
    __tablename__ = "cidades"

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String)
