from utils.db import db

class ProjectColumn(db.Model):
    __tablename__ = 'pj_column'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column( db.Integer)
    titulo = db.Column(db.String(50))
    ordem = db.Column(db.Integer)