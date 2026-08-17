# Modelo de dados de notícias.
# Biblioteca padrão.
from datetime import datetime

# Módulos internos da aplicação.
from models.base_model import BaseModel
from utils.db import db


# Define a entidade LoginNews persistida no banco de dados.
class LoginNews(BaseModel):
    __tablename__ = "noticias_login"

    id = db.Column(db.Integer, primary_key=True)
    chamada = db.Column(db.String(120), nullable=False)
    titulo = db.Column(db.String(180), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    icone = db.Column(db.String(80), nullable=False, default="pi pi-megaphone")
    cor_destaque = db.Column(db.String(20), nullable=False, default="#64ea8a")
    imagem = db.Column(db.Text)
    link = db.Column(db.Text)
    ordem = db.Column(db.Integer, nullable=False, default=0)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    atualizado_em = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
