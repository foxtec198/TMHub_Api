from functools import wraps
from datetime import datetime as dt

from flask import jsonify, request
from jwt import ExpiredSignatureError, InvalidTokenError

from models.colaboradores import Employees
from models.schedular import SchedularAccess
from models.usuarios import Users
from utils.db import db
from utils.password_security import verify_password
from utils.token import create_token, decode_token


def issue_schedular_token(access):
    return create_token({
        "tipo": "schedular",
        "acesso_id": access.id,
        "colaborador_id": access.colaborador_id,
        "perfil": access.perfil,
        "ver": int(access.token_version or 0),
    })


def decode_schedular_session():
    token = request.headers.get("Schedular-Token") or request.headers.get("Access-Token")
    if not token:
        return None, (jsonify("Token do Schedular obrigatÃ³rio."), 401)
    try:
        payload = decode_token(token)
    except ExpiredSignatureError:
        return None, (jsonify("SessÃ£o do Schedular expirada."), 401)
    except InvalidTokenError:
        return None, (jsonify("Token do Schedular invÃ¡lido."), 401)
    if payload.get("tipo") != "schedular":
        return None, (jsonify("Use uma sessÃ£o prÃ³pria do Schedular."), 401)
    access = db.session.get(SchedularAccess, payload.get("acesso_id"))
    if not access or not access.ativo or int(payload.get("ver", 0)) != int(access.token_version or 0):
        return None, (jsonify("Acesso do Schedular inativo ou invalidado."), 401)
    employee = db.session.get(Employees, access.colaborador_id)
    if not employee or employee.situacao != 1:
        return None, (jsonify("Colaborador inativo ou nÃ£o encontrado."), 403)
    return {"access": access, "employee": employee, "token": payload}, None


def schedular_route(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        session, error = decode_schedular_session()
        if error:
            return error
        kwargs["schedular_session"] = session
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            db.session.rollback()
            return jsonify("Erro com o servidor: " + str(exc)), 500
    return wrapper


def tmhub_admin_session():
    token = request.headers.get("Access-Token")
    if not token:
        return None, (jsonify("SessÃ£o administrativa obrigatÃ³ria."), 401)
    try:
        payload = decode_token(token)
    except (ExpiredSignatureError, InvalidTokenError):
        return None, (jsonify("SessÃ£o administrativa invÃ¡lida ou expirada."), 401)
    if payload.get("tipo") == "schedular":
        return None, (jsonify("Use a sessÃ£o administrativa do TMHub para esta operaÃ§Ã£o."), 401)
    user = db.session.get(Users, payload.get("id"))
    if not user or int(payload.get("ver", 0)) != int(user.token_version or 0):
        return None, (jsonify("SessÃ£o administrativa invÃ¡lida ou expirada."), 401)
    if str(user.role or "").upper() != "ADMIN":
        return None, (jsonify("Somente administradores do TMHub podem gerenciar acessos."), 403)
    return user, None


def verify_schedular_password(password, stored_hash):
    valid, legacy, needs_rehash = verify_password(password, stored_hash)
    return valid, legacy or needs_rehash
