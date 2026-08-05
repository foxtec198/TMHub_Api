from flask import jsonify, request
from jwt import ExpiredSignatureError, InvalidTokenError

from models.usuarios import Users
from utils.db import db
from utils.token import decode_token
from utils.user_requirements import auth_requirements

ONBOARDING_PATHS = {
    "/usuarios/pendencias",
    "/usuarios/onboarding/perfil",
    "/usuarios/onboarding/senha",
    "/usuarios/onboarding/senha-padrao/ignorar",
}
PUBLIC_PATHS = {"/", "/login", "/docs", "/openapi.json"}
PUBLIC_PREFIXES = ("/updates/", "/arquivos/glosas/")


def enforce_auth_state():
    if request.method == "OPTIONS":
        return None
    normalized_path = request.path.rstrip("/") or "/"
    # O Schedular possui autenticaÃ§Ã£o e sessÃ£o prÃ³prias, validadas pelas
    # rotas desse mÃ³dulo. Nunca tente interpretar seu token como usuÃ¡rio TMHub.
    if normalized_path in {"/tm-ops", "/schedular"} or normalized_path.startswith(("/tm-ops/", "/schedular/")):
        return None
    if normalized_path in PUBLIC_PATHS or normalized_path.startswith(PUBLIC_PREFIXES):
        return None
    access_token = request.headers.get("Access-Token")
    if not access_token:
        return None
    try:
        token_data = decode_token(access_token)
    except ExpiredSignatureError:
        return jsonify("Token de acesso expirado."), 401
    except InvalidTokenError:
        return jsonify("Token de acesso inválido."), 401

    user = db.session.get(Users, token_data.get("id"))
    if not user:
        return jsonify("Usuário da sessão não encontrado."), 401
    if int(token_data.get("ver", 0)) != int(user.token_version or 0):
        return jsonify("Esta sessão foi invalidada. Entre novamente."), 401

    if token_data.get("sessao_persistente") and not bool(user.token_sem_expiracao):
        return jsonify("Esta sessão contínua foi desativada. Entre novamente."), 401

    requirements = auth_requirements(user)
    if requirements["interacao_pendente"] and normalized_path not in ONBOARDING_PATHS:
        return jsonify({
            "code": "AUTH_REQUIREMENTS_PENDING",
            "message": "Conclua as etapas de segurança antes de continuar.",
            "requirements": requirements,
        }), 428
    return None
