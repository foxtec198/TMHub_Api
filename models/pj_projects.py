# Modelo de dados de projetos.
# Módulos internos da aplicação.
from utils.db import db


# Define a entidade Project persistida no banco de dados.
class Project(db.Model):
    __tablename__ = "pj_projects"
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120))
    cor = db.Column(db.String(20))
    dono = db.Column(db.Integer)