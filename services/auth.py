# ============================================= Utils
from flask import jsonify, request as rq
from utils.check_field import check_field
from utils.password_security import (
    hash_password,
    is_default_password,
    is_strong_password,
    verify_password,
)
from utils.user_requirements import auth_requirements, normalize_cpf, refresh_user_requirements
from utils.theme_access import available_themes_for, effective_theme_for
from utils.maintenance import maintenance_mode_enabled
from utils.permissions import serialize_permissions
from datetime import datetime as dt
from utils.token import create_token
from utils.limiter import limiter
from utils.session_cookie import clear_session_cookie, set_session_cookie

_LOGIN_DUMMY_HASH = "$argon2id$v=19$m=19456,t=2,p=1$sGxPv8XHtNH/EzvxE/xblw$zO/7KP4eSRn7cT82Y6178rR8umyIYlyXux0dcMi9cmU"

# =============================================  Models
from models.usuarios import Users, db

def issue_user_token(user):
    persistent = bool(user.token_sem_expiracao)
    return create_token({
        "id": user.id,
        "perm": user.role,
        "ver": int(user.token_version or 0),
        "sessao_persistente": persistent,
    }, expires=not persistent)


class AuthService:
    @limiter.limit("3 per 5 minutes")
    def login(self):
        body = rq.get_json(silent=True) or {}
        username = str(body.get("username") or "").strip()
        password = str(body.get("password") or "")

        ok, error = check_field(usuario=username, senha=password)
        if not ok: return jsonify(error), 400

        if "@" in username: user = Users.query.filter(db.func.lower(Users.email) == username.lower()).first()
        else: user = Users.query.filter_by(cpf=normalize_cpf(username)).first()

        valid, legacy_hash, needs_rehash = verify_password(
            password,
            user.hash if user else _LOGIN_DUMMY_HASH,
        )

        if legacy_hash:
            verify_password(password, _LOGIN_DUMMY_HASH)
        if not user or not user.ativo or not valid:
            return jsonify("Credenciais inválidas."), 401

        maintenance_active = maintenance_mode_enabled()
        maintenance_blocked = maintenance_active and str(user.role or "").upper() != "ADMIN"

        hash_migrated = legacy_hash or needs_rehash
        if hash_migrated: user.hash = hash_password(password)

        user.senha_padrao = is_default_password(password)
        user.troca_senha_obrigatoria = not is_strong_password(password) and not user.senha_padrao
        refresh_user_requirements(user)
        requirements = auth_requirements(user, hash_needs_migration=False)
        last_login = user.last_login
        user.last_login = dt.now()
        db.session.commit()

        token = issue_user_token(user)
        response = jsonify({
            "id": user.id,
            "display_name": user.nome,
            "access_token": token,
            "role": user.role,
            "email": user.email,
            "foto_perfil": user.foto_perfil,
            "tema": effective_theme_for(user),
            "modo_tema": user.modo_tema or "light",
            "particulas_ativas": bool(user.particulas_ativas),
            "temas_disponiveis": available_themes_for(user),
            "adorno_foto": user.adorno_foto,
            "timo_skin": user.timo_skin or "default",
            "timo_cenario": user.timo_cenario or "workshop",
            "timo_tela_inicial": bool(user.timo_tela_inicial),
            "gerencia_faltas": bool(user.gerencia_faltas),
            "permissions": serialize_permissions(user),
            "last_login": last_login,
            "primeiro_acesso": requirements["primeiro_acesso"],
            "cpf_pendente": requirements["cpf_pendente"],
            "foto_pendente": requirements["foto_pendente"],
            "troca_senha_obrigatoria": requirements["troca_senha_obrigatoria"],
            "senha_padrao": requirements["senha_padrao"],
            "hash_precisa_migracao": False,
            "hash_migrado": hash_migrated,
            "pendencia_obrigatoria": requirements["pendencia_obrigatoria"],
            "interacao_pendente": requirements["interacao_pendente"],
            "manutencao_ativa": maintenance_active,
            "manutencao_bloqueada": maintenance_blocked,
        })
        set_session_cookie(response, token, persistent=bool(user.token_sem_expiracao))
        return response, 200

    def logout(self):
        return clear_session_cookie(jsonify("Sessão encerrada.")), 200
