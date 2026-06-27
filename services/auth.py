from flask import jsonify, request as rq
from utils.token import create_token
from models.usuarios import Users, db
from utils.check_field import check_field, check_password_hash
from datetime import datetime as dt

class AuthService:
    def login(self):
        body = rq.get_json() # Obtem o JSON
        username = body.get("username") # Obtem o user (Email ou CPF)
        password = body.get("password") # Obtem a senha do usuário
        
        ok, erro = check_field(usuario=username, senha=password) # Confirma os dados (Se foram passados)
        if not ok: return jsonify(erro), 400 # Retorna BAD REQUEST caso de erro
        
        if "@" in username: user = Users().query.filter_by(email=username).first() # Confirma se tem arroba no username
        else: user = Users().query.filter_by(cpf=username).first() # Caso contrario busca por CPF

        if not user: return jsonify("Usuário nao encontrado!"), 404 # Retorna NOT FOUND, 404
        if not check_password_hash(password, user.hash): return jsonify("Senha incorreta!"), 400 # Confirma se a senha esta correta
        token = create_token({"id": user.id, "perm": user.perm}) # Cria o access_token
        last_login = user.last_login # Salva o ultimo login registrado
        user.last_login = dt.now() # Atualiza o ultimo login (Atual)
        db.session.commit() # Salva os dados

        return jsonify({
            "display_name": user.nome, 
            "access_token": token, 
            "role": user.role, 
            "last_login": last_login
        }), 200