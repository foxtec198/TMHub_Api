from flask import request as rq, jsonify
from models.usuarios import Users, db
from utils.check_field import check_field
from hashlib import sha256
from utils.safe_route import safe_route
from datetime import datetime as dt, timedelta
from email.message import EmailMessage
from os import getenv
import re
import secrets
import smtplib

PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9\s]).{8,}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHOTO_PATTERN = re.compile(r"^data:image/(png|jpe?g|webp);base64,[A-Za-z0-9+/=]+$")

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

    @safe_route
    def profile(self, token_data):
        user = db.session.get(Users, token_data.get("id"))
        if not user:
            return jsonify("Usuário não encontrado."), 404
        return jsonify(self._serialize(user))

    @safe_route
    def update_profile(self, token_data):
        user = db.session.get(Users, token_data.get("id"))
        if not user:
            return jsonify("Usuário não encontrado."), 404

        body = rq.get_json(silent=True) or {}
        nome = body.get("nome")
        foto = body.get("foto_perfil")
        senha_atual = body.get("senha_atual")
        nova_senha = body.get("nova_senha")

        if nome is not None:
            nome = nome.strip()
            if len(nome) < 2 or len(nome) > 120:
                return jsonify("O nome deve ter entre 2 e 120 caracteres."), 400
            user.nome = nome

        if foto is not None:
            if foto and (len(foto) > 2_000_000 or not PHOTO_PATTERN.fullmatch(foto)):
                return jsonify("A foto deve ser PNG, JPG ou WEBP e ter até 1,5 MB."), 400
            user.foto_perfil = foto or None

        if nova_senha is not None:
            if sha256(str(senha_atual or "").encode()).hexdigest() != user.hash:
                return jsonify("Senha atual incorreta."), 400
            if not PASSWORD_PATTERN.fullmatch(nova_senha):
                return jsonify("A senha deve ter ao menos 8 caracteres, com maiúscula, minúscula, número e caractere especial."), 400
            user.hash = sha256(nova_senha.encode()).hexdigest()

        if not any(value is not None for value in (nome, foto, nova_senha)):
            return jsonify("Nenhuma alteração informada."), 400

        db.session.commit()
        return jsonify(self._serialize(user))

    @safe_route
    def request_email_code(self, token_data):
        user = db.session.get(Users, token_data.get("id"))
        body = rq.get_json(silent=True) or {}
        email = str(body.get("email", "")).strip().lower()
        if not user:
            return jsonify("Usuário não encontrado."), 404
        if not EMAIL_PATTERN.fullmatch(email):
            return jsonify("Informe um e-mail válido."), 400
        if Users.query.filter(Users.email == email, Users.id != user.id).first():
            return jsonify("Este e-mail já está em uso."), 409

        code = f"{secrets.randbelow(1_000_000):06d}"
        try:
            self._send_email_code(email, code)
        except (OSError, RuntimeError, smtplib.SMTPException):
            return jsonify("O serviço de e-mail não está disponível no momento."), 503
        user.email_pendente = email
        user.email_codigo_hash = sha256(code.encode()).hexdigest()
        user.email_codigo_expira_em = dt.now() + timedelta(minutes=10)
        db.session.commit()
        return jsonify("Código enviado. Ele expira em 10 minutos."), 200

    @safe_route
    def confirm_email(self, token_data):
        user = db.session.get(Users, token_data.get("id"))
        code = str((rq.get_json(silent=True) or {}).get("codigo", "")).strip()
        if not user:
            return jsonify("Usuário não encontrado."), 404
        if not user.email_pendente or not user.email_codigo_hash:
            return jsonify("Solicite um novo código de verificação."), 400
        if not user.email_codigo_expira_em or user.email_codigo_expira_em < dt.now():
            return jsonify("O código expirou. Solicite um novo."), 400
        if sha256(code.encode()).hexdigest() != user.email_codigo_hash:
            return jsonify("Código de verificação inválido."), 400

        user.email = user.email_pendente
        user.email_pendente = None
        user.email_codigo_hash = None
        user.email_codigo_expira_em = None
        db.session.commit()
        return jsonify(self._serialize(user))

    @staticmethod
    def _serialize(user):
        return {"id": user.id, "nome": user.nome, "email": user.email, "foto_perfil": user.foto_perfil, "role": user.role}

    @staticmethod
    def _send_email_code(recipient, code):
        host = getenv("SMTP_HOST")
        sender = getenv("SMTP_FROM") or getenv("SMTP_USER")
        if not host or not sender:
            raise RuntimeError("SMTP_HOST e SMTP_FROM (ou SMTP_USER) devem estar configurados.")

        message = EmailMessage()
        message["Subject"] = "Confirme a troca de e-mail - TM Hub"
        message["From"] = sender
        message["To"] = recipient
        message.set_content(f"Seu código de verificação é {code}. Ele expira em 10 minutos.")

        port = int(getenv("SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            if getenv("SMTP_STARTTLS", "true").lower() == "true":
                smtp.starttls()
            username = getenv("SMTP_USER")
            password = getenv("SMTP_PASSWORD")
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
