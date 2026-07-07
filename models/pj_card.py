from utils.db import db

class ProjectCard(db.Model):
    __tablename__ = 'pj_card'
    
    id = db.Column(db.Integer, primary_key=True)
    column_id = db.Column(db.Integer)
    titulo = db.Column(db.String(120))
    descricao = db.Column(db.Text)
    etiqueta = db.Column(db.String(50))
    ordem = db.Column(db.Integer)