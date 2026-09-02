"""Provedor OpenID Connect restrito ao cliente Jellyfin do TMHub."""

from base64 import b64decode, urlsafe_b64encode
from datetime import datetime as dt, timedelta, timezone
from hashlib import sha256
from os import getenv
from re import sub
from secrets import token_urlsafe
from unicodedata import normalize
from urllib.parse import urlencode

import jwt
from cryptography.hazmat.primitives import serialization
from flask import jsonify, make_response, redirect, request as rq

from models.oidc import OidcAuthorizationCode, OidcLoginTicket
from models.usuarios import Users
from utils.db import db


SESSION_COOKIE = "tmhub_oidc_session"
LOGIN_TICKET_TTL = timedelta(seconds=60)
AUTHORIZATION_CODE_TTL = timedelta(minutes=2)
OIDC_SESSION_TTL = timedelta(minutes=5)
ACCESS_TOKEN_TTL = timedelta(minutes=5)


def _setting(name, default=""):
    return str(getenv(name, default) or "").strip()


def _issuer():
    return _setting("OIDC_ISSUER_URL", "https://api.tmhub.hubbix.com.br/oidc").rstrip("/")


def _client_id():
    return _setting("OIDC_CLIENT_ID", "jellyfin")


def _redirect_uris():
    configured = _setting(
        "OIDC_REDIRECT_URIS",
        "https://stream.tmhub.hubbix.com.br/sso/OID/redirect/tmhub",
    )
    return {item.strip() for item in configured.split(",") if item.strip()}


def _jellyfin_start_url():
    return _setting(
        "JELLYFIN_SSO_START_URL",
        "https://stream.tmhub.hubbix.com.br/sso/OID/start/tmhub",
    )


def _hash_secret(value):
    return sha256(str(value).encode("utf-8")).hexdigest()


def _b64url(value):
    return urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _private_key():
    encoded = _setting("OIDC_RSA_PRIVATE_KEY_B64")
    if encoded:
        try:
            value = b64decode(encoded, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as error:
            raise RuntimeError("OIDC_RSA_PRIVATE_KEY_B64 invalida") from error
    else:
        value = _setting("OIDC_RSA_PRIVATE_KEY").replace("\\n", "\n")
    if not value:
        raise RuntimeError("OIDC_RSA_PRIVATE_KEY nao configurada")
    return serialization.load_pem_private_key(value.encode("utf-8"), password=None)


def _key_id():
    return _setting("OIDC_KEY_ID", "tmhub-jellyfin-1")


def _client_secret_valid(provided):
    expected = _setting("OIDC_CLIENT_SECRET")
    if not expected:
        return not provided
    if not provided:
        return False
    from hmac import compare_digest

    return compare_digest(provided, expected)


def _public_jwk():
    numbers = _private_key().public_key().public_numbers()
    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": _key_id(),
        "n": _b64url(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
        "e": _b64url(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")),
    }


def _username(user):
    # O vinculo continua usando o sub (ID imutavel), nunca este nome legivel.
    name = normalize("NFKD", user.nome or "").encode("ascii", "ignore").decode().lower()
    parts = [sub(r"[^a-z0-9]", "", part) for part in name.split()]
    parts = [part for part in parts if part]
    return ".".join(parts[:2]) or f"tmhub-{user.id}"


def _groups(user):
    groups = ["jellyfin_user"]
    configured_admin_ids = {
        item.strip()
        for item in _setting("OIDC_JELLYFIN_ADMIN_USER_IDS").split(",")
        if item.strip()
    }
    if str(user.id) in configured_admin_ids:
        groups.append("jellyfin_admin")
    return groups


def _claims(user):
    return {
        "sub": str(user.id),
        "preferred_username": _username(user),
        "name": user.nome or _username(user),
        "email": user.email or "",
        "email_verified": bool(user.email),
        "groups": _groups(user),
    }


def _sign(payload):
    return jwt.encode(
        payload,
        _private_key(),
        algorithm="RS256",
        headers={"kid": _key_id(), "typ": "JWT"},
    )


def _oauth_error(error, description, status=400):
    response = jsonify({"error": error, "error_description": description})
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return response


def _redirect_error(redirect_uri, state, error, description):
    params = {"error": error, "error_description": description}
    if state:
        params["state"] = state
    separator = "&" if "?" in redirect_uri else "?"
    return redirect(f"{redirect_uri}{separator}{urlencode(params)}")


class OidcService:
    def create_jellyfin_ticket(self, token_data):
        user = db.session.get(Users, (token_data or {}).get("id"))
        if not user:
            return jsonify("Usuario da sessao nao encontrado."), 401

        raw_ticket = token_urlsafe(32)
        db.session.add(OidcLoginTicket(
            token_hash=_hash_secret(raw_ticket),
            usuario_id=user.id,
            expira_em=dt.now() + LOGIN_TICKET_TTL,
        ))
        db.session.commit()
        return jsonify({
            "entry_url": f"{_issuer()}/session?ticket={raw_ticket}",
            "expires_in": int(LOGIN_TICKET_TTL.total_seconds()),
        })

    def establish_session(self):
        raw_ticket = str(rq.args.get("ticket") or "")
        ticket = (
            OidcLoginTicket.query
            .filter_by(token_hash=_hash_secret(raw_ticket))
            .with_for_update()
            .first()
        )
        now = dt.now()
        if not raw_ticket or not ticket or ticket.consumido_em or ticket.expira_em <= now:
            return _oauth_error("invalid_request", "O acesso temporario expirou.", 401)

        user = db.session.get(Users, ticket.usuario_id)
        if not user:
            return _oauth_error("access_denied", "Usuario nao encontrado.", 401)

        ticket.consumido_em = now
        db.session.commit()
        token_now = dt.now(timezone.utc)
        session_secret = _setting("SECRET")
        if not session_secret:
            return _oauth_error("temporarily_unavailable", "SECRET nao configurada.", 503)
        session_token = jwt.encode({
            "sub": str(user.id),
            "typ": "oidc_session",
            "iat": token_now,
            "exp": token_now + OIDC_SESSION_TTL,
            "ver": int(user.token_version or 0),
        }, session_secret, algorithm="HS256")

        response = make_response(redirect(_jellyfin_start_url()))
        response.set_cookie(
            SESSION_COOKIE,
            session_token,
            max_age=int(OIDC_SESSION_TTL.total_seconds()),
            secure=True,
            httponly=True,
            samesite="Lax",
            path="/oidc",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    def discovery(self):
        issuer = _issuer()
        authentication_methods = (
            ["client_secret_post", "client_secret_basic"]
            if _setting("OIDC_CLIENT_SECRET")
            else ["none"]
        )
        return jsonify({
            "issuer": issuer,
            "authorization_endpoint": f"{issuer}/authorize",
            "token_endpoint": f"{issuer}/token",
            "userinfo_endpoint": f"{issuer}/userinfo",
            "jwks_uri": f"{issuer}/jwks",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "token_endpoint_auth_methods_supported": authentication_methods,
            "scopes_supported": ["openid", "profile", "email", "groups"],
            "claims_supported": [
                "sub", "preferred_username", "name", "email", "email_verified", "groups",
            ],
            "code_challenge_methods_supported": ["S256"],
        })

    def jwks(self):
        try:
            return jsonify({"keys": [_public_jwk()]})
        except RuntimeError as error:
            return _oauth_error("temporarily_unavailable", str(error), 503)

    def authorize(self):
        client_id = str(rq.args.get("client_id") or "")
        redirect_uri = str(rq.args.get("redirect_uri") or "")
        state = str(rq.args.get("state") or "")
        response_type = str(rq.args.get("response_type") or "")
        scope = str(rq.args.get("scope") or "")
        nonce = str(rq.args.get("nonce") or "") or None
        code_challenge = str(rq.args.get("code_challenge") or "") or None
        challenge_method = str(rq.args.get("code_challenge_method") or "") or None

        if client_id != _client_id() or redirect_uri not in _redirect_uris():
            return _oauth_error("invalid_request", "Cliente ou retorno OIDC invalido.")
        if response_type != "code":
            return _redirect_error(redirect_uri, state, "unsupported_response_type", "Use authorization code.")
        scopes = set(scope.split())
        if "openid" not in scopes:
            return _redirect_error(redirect_uri, state, "invalid_scope", "O escopo openid e obrigatorio.")
        if not code_challenge or challenge_method != "S256":
            return _redirect_error(
                redirect_uri,
                state,
                "invalid_request",
                "PKCE S256 e obrigatorio.",
            )

        session_token = rq.cookies.get(SESSION_COOKIE)
        try:
            session = jwt.decode(session_token, _setting("SECRET"), algorithms=["HS256"])
        except Exception:
            return _redirect_error(redirect_uri, state, "login_required", "Abra a Midia pelo TMHub.")
        if session.get("typ") != "oidc_session":
            return _redirect_error(redirect_uri, state, "login_required", "Sessao OIDC invalida.")

        user = db.session.get(Users, int(session.get("sub")))
        if not user or int(session.get("ver", -1)) != int(user.token_version or 0):
            return _redirect_error(redirect_uri, state, "login_required", "Sessao do TMHub invalidada.")

        raw_code = token_urlsafe(40)
        db.session.add(OidcAuthorizationCode(
            code_hash=_hash_secret(raw_code),
            usuario_id=user.id,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=" ".join(sorted(scopes)),
            nonce=nonce,
            code_challenge=code_challenge,
            code_challenge_method=challenge_method,
            expira_em=dt.now() + AUTHORIZATION_CODE_TTL,
        ))
        db.session.commit()
        params = {"code": raw_code}
        if state:
            params["state"] = state
        separator = "&" if "?" in redirect_uri else "?"
        response = make_response(redirect(f"{redirect_uri}{separator}{urlencode(params)}"))
        response.delete_cookie(SESSION_COOKIE, path="/oidc", secure=True, httponly=True, samesite="Lax")
        response.headers["Cache-Control"] = "no-store"
        return response

    def token(self):
        if str(rq.form.get("grant_type") or "") != "authorization_code":
            return _oauth_error("unsupported_grant_type", "Use authorization_code.")

        client_id = str(rq.form.get("client_id") or "")
        client_secret = str(rq.form.get("client_secret") or "")
        if rq.authorization and rq.authorization.type.lower() == "basic":
            client_id = rq.authorization.username or client_id
            client_secret = rq.authorization.password or client_secret
        if client_id != _client_id() or not _client_secret_valid(client_secret):
            return _oauth_error("invalid_client", "Credenciais do cliente invalidas.", 401)

        raw_code = str(rq.form.get("code") or "")
        code = (
            OidcAuthorizationCode.query
            .filter_by(code_hash=_hash_secret(raw_code))
            .with_for_update()
            .first()
        )
        now = dt.now()
        redirect_uri = str(rq.form.get("redirect_uri") or "")
        if (
            not raw_code
            or not code
            or code.consumido_em
            or code.expira_em <= now
            or code.client_id != client_id
            or code.redirect_uri != redirect_uri
        ):
            return _oauth_error("invalid_grant", "Codigo invalido ou expirado.")

        if code.code_challenge:
            verifier = str(rq.form.get("code_verifier") or "")
            try:
                calculated = _b64url(sha256(verifier.encode("ascii")).digest()) if verifier else ""
            except UnicodeEncodeError:
                calculated = ""
            if calculated != code.code_challenge:
                return _oauth_error("invalid_grant", "Verificacao PKCE invalida.")

        user = db.session.get(Users, code.usuario_id)
        if not user:
            return _oauth_error("invalid_grant", "Usuario nao encontrado.")

        token_now = dt.now(timezone.utc)
        common = {
            "iss": _issuer(),
            "sub": str(user.id),
            "aud": client_id,
            "iat": token_now,
            "exp": token_now + ACCESS_TOKEN_TTL,
            **_claims(user),
        }
        id_payload = {**common, "typ": "id_token"}
        if code.nonce:
            id_payload["nonce"] = code.nonce
        try:
            access_token = _sign({**common, "typ": "access_token", "scope": code.scope})
            id_token = _sign(id_payload)
        except RuntimeError as error:
            db.session.rollback()
            return _oauth_error("temporarily_unavailable", str(error), 503)

        code.consumido_em = now
        db.session.commit()
        response = jsonify({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": int(ACCESS_TOKEN_TTL.total_seconds()),
            "id_token": id_token,
            "scope": code.scope,
        })
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        return response

    def userinfo(self):
        authorization = str(rq.headers.get("Authorization") or "")
        if not authorization.startswith("Bearer "):
            return _oauth_error("invalid_token", "Bearer token obrigatorio.", 401)
        try:
            payload = jwt.decode(
                authorization[7:],
                _private_key().public_key(),
                algorithms=["RS256"],
                audience=_client_id(),
                issuer=_issuer(),
            )
        except Exception:
            return _oauth_error("invalid_token", "Token invalido ou expirado.", 401)
        try:
            user_id = int(payload.get("sub"))
        except (TypeError, ValueError):
            return _oauth_error("invalid_token", "Token sem usuario valido.", 401)
        user = db.session.get(Users, user_id)
        if not user:
            return _oauth_error("invalid_token", "Usuario nao encontrado.", 401)
        return jsonify(_claims(user))
