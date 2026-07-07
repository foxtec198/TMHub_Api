from utils.db import db

class ProjectCardMember(db.Model):
    __tablename__ = 'pj_card_member'
    
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer)
    employee_id = db.Column(db.Integer)