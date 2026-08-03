from utils.db import db
from models.base_model import BaseModel
from datetime import datetime as dt

class Users(BaseModel):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String)
    email = db.Column(db.String)
    cpf = db.Column(db.String, unique=True, nullable=True)
    hash = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=dt.now)
    last_login = db.Column(db.DateTime)
    role = db.Column(db.String, default="USER")
    foto_perfil = db.Column(db.Text)
    tema = db.Column(db.String(10), default="light")
    gerencia_faltas = db.Column(db.Boolean, nullable=False, default=False)
    email_pendente = db.Column(db.String)
    email_codigo_hash = db.Column(db.String)
    email_codigo_expira_em = db.Column(db.DateTime)
    primeiro_acesso = db.Column(db.Boolean, nullable=False, default=True)
    cpf_pendente = db.Column(db.Boolean, nullable=False, default=True)
    foto_pendente = db.Column(db.Boolean, nullable=False, default=True)
    troca_senha_obrigatoria = db.Column(db.Boolean, nullable=False, default=False)
    senha_padrao = db.Column(db.Boolean, nullable=False, default=False)
    # Destinado apenas a telas de exibição contínua (ODS/KDS). Esta flag é
    # administrada diretamente no banco e não é exposta nas configurações.
    token_sem_expiracao = db.Column(db.Boolean, nullable=False, default=False)
    token_version = db.Column(db.Integer, nullable=False, default=0)
    senha_alterada_em = db.Column(db.DateTime)
    filiais = db.relationship("Branch", secondary="filial_usuarios", back_populates="usuarios")
    permissoes = db.relationship(
        "UserPermission",
        cascade="all, delete-orphan",
        passive_deletes=True,
        backref="usuario",
    )
