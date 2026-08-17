# Modelo de dados de situações.
# Módulos internos da aplicação.
from models.base_model import BaseModel
from utils.db import db

# Define a entidade Situations persistida no banco de dados.
class Situations(BaseModel):
    __tablename__ = "situacoes"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String)
