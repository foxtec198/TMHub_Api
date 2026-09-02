"""Rotas OIDC e ponte autenticada para o Jellyfin."""

from flask import Blueprint

from services.oidc import OidcService
from utils.safe_route import safe_route


oidc_bp = Blueprint("OpenIDConnect", __name__)
jellyfin_bp = Blueprint("JellyfinSSO", __name__)
service = OidcService()


@jellyfin_bp.post("/ticket")
@safe_route
def create_ticket(token_data):
    return service.create_jellyfin_ticket(token_data)


@oidc_bp.get("/.well-known/openid-configuration")
def discovery():
    return service.discovery()


@oidc_bp.get("/jwks")
def jwks():
    return service.jwks()


@oidc_bp.get("/session")
def establish_session():
    return service.establish_session()


@oidc_bp.get("/authorize")
def authorize():
    return service.authorize()


@oidc_bp.post("/token")
def token():
    return service.token()


@oidc_bp.get("/userinfo")
def userinfo():
    return service.userinfo()
