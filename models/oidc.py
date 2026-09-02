"""Persistencia curta do fluxo OIDC usado pelo Jellyfin."""

from datetime import datetime as dt

from utils.db import db


class OidcLoginTicket(db.Model):
    __tablename__ = "oidc_login_tickets"

    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expira_em = db.Column(db.DateTime, nullable=False, index=True)
    consumido_em = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=dt.now)


class OidcAuthorizationCode(db.Model):
    __tablename__ = "oidc_authorization_codes"

    id = db.Column(db.Integer, primary_key=True)
    code_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_id = db.Column(db.String(120), nullable=False)
    redirect_uri = db.Column(db.Text, nullable=False)
    scope = db.Column(db.Text, nullable=False)
    nonce = db.Column(db.Text, nullable=True)
    code_challenge = db.Column(db.Text, nullable=True)
    code_challenge_method = db.Column(db.String(12), nullable=True)
    expira_em = db.Column(db.DateTime, nullable=False, index=True)
    consumido_em = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=dt.now)
