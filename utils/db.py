# Utilitários de conexão com o banco de dados.
# db_manager.py
# Dependências externas.
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, create_engine
# Biblioteca padrão.
from os import environ

db = SQLAlchemy()
