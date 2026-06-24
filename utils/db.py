# db_manager.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, create_engine
from os import environ

db = SQLAlchemy()