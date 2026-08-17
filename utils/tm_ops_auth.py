# Utilitários de autenticação do TM Ops.
# Biblioteca padrão.
from functools import wraps

# Dependências externas.
from flask import jsonify, request
from jwt import ExpiredSignatureError, InvalidTokenError

# Módulos internos da aplicação.
from models.colaboradores import Employees
from models.usuarios import Users
from utils.db import db
from utils.password_security import verify_password
from utils.token import create_token, decode_token


def issue_tm_ops_token(employee):
    return create_token({
        "tipo": "tm_ops",
        "colaborador_id": employee.id,
        "perfil": employee.tm_ops_perfil or "executor",
        "ver": int(employee.tm_ops_token_version or 0),
    })


def decode_tm_ops_session():
    token = (
        request.headers.get("TM-Ops-Token")
        or request.headers.get("Schedular-Token")
        or request.headers.get("Access-Token")
    )
    if not token:
        return None, (jsonify("Token do TM Ops obrigatório."), 401)
    try:
        payload = decode_token(token)
    except ExpiredSignatureError:
        return None, (jsonify("Sessão do TM Ops expirada."), 401)
    except InvalidTokenError:
        return None, (jsonify("Token do TM Ops inválido."), 401)
    if payload.get("tipo") not in {"tm_ops", "schedular"}:
        return None, (jsonify("Use uma sessão própria do TM Ops."), 401)

    employee = db.session.get(Employees, payload.get("colaborador_id"))
    if not employee or employee.situacao != 1:
        return None, (jsonify("Colaborador inativo ou não encontrado."), 403)
    if not employee.tm_ops_ativo or not employee.tm_ops_password_hash:
        return None, (jsonify("Acesso ao TM Ops inativo ou não autorizado."), 401)
    if int(payload.get("ver", 0)) != int(employee.tm_ops_token_version or 0):
        return None, (jsonify("Sessão do TM Ops invalidada."), 401)
    return {"employee": employee, "token": payload}, None


def tm_ops_route(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        session, error = decode_tm_ops_session()
        if error:
            return error
        kwargs["tm_ops_session"] = session
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            db.session.rollback()
            return jsonify("Erro com o servidor: " + str(exc)), 500
    return wrapper


def tmhub_admin_session():
    token = request.headers.get("Access-Token")
    if not token:
        return None, (jsonify("Sessão administrativa obrigatória."), 401)
    try:
        payload = decode_token(token)
    except (ExpiredSignatureError, InvalidTokenError):
        return None, (jsonify("Sessão administrativa inválida ou expirada."), 401)
    if payload.get("tipo") in {"tm_ops", "schedular"}:
        return None, (jsonify("Use a sessão administrativa do TM Hub para esta operação."), 401)
    user = db.session.get(Users, payload.get("id"))
    if not user or int(payload.get("ver", 0)) != int(user.token_version or 0):
        return None, (jsonify("Sessão administrativa inválida ou expirada."), 401)
    if str(user.role or "").upper() != "ADMIN":
        return None, (jsonify("Somente administradores do TM Hub podem gerenciar acessos."), 403)
    return user, None


def verify_tm_ops_password(password, stored_hash):
    valid, legacy, needs_rehash = verify_password(password, stored_hash)
    return valid, legacy or needs_rehash


# Aliases temporários para integrações que ainda importam os nomes antigos.
issue_schedular_token = issue_tm_ops_token
decode_schedular_session = decode_tm_ops_session
schedular_route = tm_ops_route
verify_schedular_password = verify_tm_ops_password
