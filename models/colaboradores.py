from utils.db import db
from models.base_model import BaseModel
from datetime import datetime as dt

class Employees(BaseModel):
    __tablename__ = "colaboradores"

    # A matricula e a identidade canonica do colaborador. O banco possui uma
    # constraint que garante que os dois campos continuem iguais.
    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    matricula = db.Column(db.Integer, nullable=False, unique=True)
    nome = db.Column(db.String)
    data_admissao = db.Column(db.DateTime, default=dt.now())
    cargo = db.Column(db.Integer)
    carga_horaria  =  db.Column(db.Integer)

    centro_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "centro_de_custo.id",
            ondelete="SET NULL"
        )
    )
    
    situacao = db.Column(
        db.Integer,
        db.ForeignKey(
            "situacoes.id",
            ondelete="SET NULL"
        ),
    )
