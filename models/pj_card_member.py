# Modelo de dados de membros de cards.
# Módulos internos da aplicação.
from utils.db import db

# Define a entidade ProjectCardMember persistida no banco de dados.
class ProjectCardMember(db.Model):
    __tablename__ = 'pj_card_member'
    
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer)
    employee_id = db.Column(db.Integer)
