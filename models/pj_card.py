# Modelo de dados de cards de projeto.
# Módulos internos da aplicação.
from utils.db import db
# Biblioteca padrão.
from datetime import datetime as dt

# Define a entidade ProjectCard persistida no banco de dados.
class ProjectCard(db.Model):
    __tablename__ = 'pj_card'
    
    id = db.Column(db.Integer, primary_key=True)
    column_id = db.Column(db.Integer)
    titulo = db.Column(db.String(120))
    descricao = db.Column(db.Text)
    etiqueta = db.Column(db.String(50))
    ordem = db.Column(db.Integer)
    data_inicio = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now, index=True)
    data_fim = db.Column(db.DateTime(timezone=True), index=True)
    concluida_em = db.Column(db.DateTime(timezone=True), index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now, onupdate=dt.now)
