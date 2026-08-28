# Modelo de dados de supervisores.
# Módulos internos da aplicação.
from utils.db import db
from models.base_model import BaseModel

# Define a entidade Supervisors persistida no banco de dados.
class Supervisors(BaseModel):
    __tablename__ = "supervisores"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String)
    # Usuário autenticável que responde pelo supervisor operacional. Registros
    # sem esse vínculo são mantidos apenas para leitura histórica.
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="SET NULL"),
        unique=True,
        index=True,
    )
