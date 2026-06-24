# ./app.py
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from os import getenv
from utils.blueprints import blueprints
from utils.db import db

load_dotenv() # Carrega o dotenv

# Variaveis de Instancia
DEBUG = getenv("DEBUG")
PORT = getenv("PORT", 8590)
HOST = getenv("HOST")

# Variaveis Comuns
app = Flask(__name__)
CORS(app, allow_headers="*") # Carrega os CORS security

# Configs do APP
app.config["SECRET_KEY"] = getenv("SECRET")
app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DB_URI")

# Carrega os BPS das Rotas
for bp in blueprints: app.register_blueprint(bp, url_prefix=blueprints[bp])
db.init_app(app) # Inicia o banco de dados
with app.app_context(): db.create_all() # Cria as tabelas

# Inicia o servidor
if __name__ == "__main__": app.run(debug=DEBUG, port=PORT, host=HOST)