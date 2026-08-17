# Utilitários de proteção de autenticação.
# Dependências externas.
from flask import jsonify, request
from jwt import ExpiredSignatureError, InvalidTokenError

# Módulos internos da aplicação.
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
AGENT_ALLOWED_PATHS = {"/timo/process", "/timo/agentes/tema"}

def enforce_auth_state():
    if request.method == "OPTIONS": return None
    normalized_path = request.path.rstrip("/") or "/"
    if normalized_path in {"/tm-ops", "/schedular"} or normalized_path.startswith(("/tm-ops/", "/schedular/")): return None
    if normalized_path in PUBLIC_PATHS or normalized_path.startswith(PUBLIC_PREFIXES): return None
    access_token = request.headers.get("Access-Token")
    if not access_token: return None

    try: token_data = decode_token(access_token)
    except ExpiredSignatureError: return jsonify("Token de acesso expirado."), 401
    except InvalidTokenError: return jsonify("Token de acesso inválido."), 401

    is_timo_voice_agent = token_data.get("typ") == "timo_voice_agent"
    if is_timo_voice_agent and normalized_path not in AGENT_ALLOWED_PATHS:
        return jsonify("A credencial do Timo Voice Agent não permite esta operação."), 403

    user = db.session.get(Users, token_data.get("id"))
    if not user:
        return jsonify("Usuário da sessão não encontrado."), 401
    # O token do agente possui uma versão própria, diferente da versão de sessão
    # do usuário. A validação completa (agente + proprietário) ocorre no serviço
    # do Timo antes de processar qualquer comando.
    if is_timo_voice_agent:
        return None
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
