from utils.db import db
from models.base_model import BaseModel
from datetime import datetime as dt

class Vacancy(BaseModel):
    __tablename__ = "ad_vagas"

    id = db.Column(db.Integer, primary_key=True)

    # Colaborador que saiu (import automático pela matrícula)
    matricula = db.Column(db.String, nullable=False)
    colaborador = db.Column(db.String, nullable=False)
    departamento = db.Column(db.String)
    centro_custo = db.Column(db.String)
    centro_id = db.Column(db.Integer)
    funcao = db.Column(db.String)
    carga_horaria = db.Column(db.Integer)

    # Preenchimento manual
    horario_trabalho = db.Column(db.String)
    motivo_saida = db.Column(db.String)

    # Status da vaga
    status = db.Column(db.String, default="aberta")

    # Dados obrigatórios ao mover a vaga para "Entrevista"
    entrevistador = db.Column(db.String)
    entrevista_data = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=dt.now)
    updated_at = db.Column(db.DateTime, default=dt.now, onupdate=dt.now)
