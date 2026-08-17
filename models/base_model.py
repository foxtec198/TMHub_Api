# Modelo de dados de entidades SQLAlchemy.
# models/base_model.py
# Módulos internos da aplicação.
from utils.db import db

# Define a entidade BaseModel persistida no banco de dados.
class BaseModel(db.Model):
    __abstract__ = True

    def to_dict(self):
        return {
            c.name: 
                getattr(
                    self, 
                    c.name
                ) for c in self.__table__.columns
        }
