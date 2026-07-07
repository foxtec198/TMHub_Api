from utils.db import db

class ProjectMember(db.Model):
    __tablename__ = 'pj_member'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer)
    employee_id = db.Column(db.Integer)