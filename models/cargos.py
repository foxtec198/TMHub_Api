# Modelo de dados de cargos.
# Módulos internos da aplicação.
from models.base_model import BaseModel
from utils.db import db


# Define a entidade Cargos persistida no banco de dados.
class Cargos(BaseModel):
    __tablename__ = "cargos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String)
    multa = db.Column(db.Float)
    # Configuração usada no pagamento quando outro cargo cobre este posto.
    adicional_tipo = db.Column(db.String(100))
    adicional_valor_diaria = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    active = db.Column(db.Boolean)
