from models.base_model import BaseModel
from utils.db import db
from datetime import datetime as dt

class Floaters(BaseModel):
    __tablename__ = "volantes"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=dt.now())
    employee_id = db.Column(db.Integer)
    was_used = db.Column(db.Integer, default=0)