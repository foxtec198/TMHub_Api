from flask import request as rq, jsonify
from models.usuarios import Users, db
from utils.check_field import check_field
from hashlib import sha256
from utils.safe_route import safe_route

class UserServices:
    def read(self):
        allUser = db.session.query(Users.id, Users.nome).all()
        return jsonify([u._asdict() for u in allUser])

    @safe_route
    def create(self):
        # Dados vindos do request
        body = rq.get_json()
        nome = body.get("nome")
        cpf = body.get("cpf")
        email = body.get("email")
        pwd = body.get("password")

        ok, error = check_field(nome=nome, cpf=cpf, senha=pwd)
        if not ok:
            return jsonify(error), 400  # Retorna BAD REQUEST

        new_user = Users(nome=nome, cpf=cpf, hash=sha256(str(pwd).encode()).hexdigest())
        if email:
            new_user.email = email  # Seta o email somente se houver

        db.session.add(new_user)  # Adiciona o novo usuario ao banco
        db.session.commit()  # Commit geral

        # Retoran 201, CREATED
        return jsonify("Usuário criado com sucesso!"), 201

    @safe_route
    def update(self): ...

    @safe_route
    def delete(self): ...
