# Regras de negócio de autenticação.
# Biblioteca padrão.
from datetime import datetime as dt

# Dependências externas.
from flask import jsonify, request as rq

# Módulos internos da aplicação.
from models.usuarios import Users, db
from utils.check_field import check_field
from utils.password_security import (
    hash_password,
    is_default_password,
    is_strong_password,
    verify_password,
)
from utils.permissions import serialize_permissions
from utils.token import create_token
from utils.user_requirements import auth_requirements, normalize_cpf, refresh_user_requirements
from utils.maintenance import maintenance_mode_enabled
from utils.theme_access import available_themes_for, effective_theme_for


def issue_user_token(user):
    persistent = bool(user.token_sem_expiracao)
    return create_token({
        "id": user.id,
        "perm": user.role,
        "ver": int(user.token_version or 0),
        "sessao_persistente": persistent,
    }, expires=not persistent)


class AuthService:
    def login(self):
        body = rq.get_json(silent=True) or {}
        username = str(body.get("username") or "").strip()
        password = str(body.get("password") or "")

        ok, error = check_field(usuario=username, senha=password)
        if not ok:
            return jsonify(error), 400

        if "@" in username:
            user = Users.query.filter(db.func.lower(Users.email) == username.lower()).first()
        else:
            user = Users.query.filter_by(cpf=normalize_cpf(username)).first()
        if not user:
            return jsonify("Usuário não encontrado!"), 404

        valid, legacy_hash, needs_rehash = verify_password(password, user.hash)
        if not valid:
            return jsonify("Senha incorreta!"), 400

        maintenance_active = maintenance_mode_enabled()
        maintenance_blocked = maintenance_active and str(user.role or "").upper() != "ADMIN"

        hash_migrated = legacy_hash or needs_rehash
        if hash_migrated:
            user.hash = hash_password(password)

        user.senha_padrao = is_default_password(password)
        user.troca_senha_obrigatoria = not is_strong_password(password) and not user.senha_padrao
        refresh_user_requirements(user)
        requirements = auth_requirements(user, hash_needs_migration=False)
        last_login = user.last_login
        user.last_login = dt.now()
        db.session.commit()

        return jsonify({
            "id": user.id,
            "display_name": user.nome,
            "access_token": None if maintenance_blocked else issue_user_token(user),
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
        }), 200
