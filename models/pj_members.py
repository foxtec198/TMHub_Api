# Modelo de dados de membros de projeto.
# Módulos internos da aplicação.
from utils.db import db

# Define a entidade ProjectMember persistida no banco de dados.
class ProjectMember(db.Model):
    __tablename__ = 'pj_member'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer)
    employee_id = db.Column(db.Integer)
