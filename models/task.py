from utils.db import db
from models.base_model import BaseModel
from datetime import datetime as dt

class Task(BaseModel):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    status = db.Column(db.String, default="pending")
    command = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=dt.now())
    ended_at = db.Column(db.DateTime)