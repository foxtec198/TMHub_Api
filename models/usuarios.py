# Modelo de dados de usuários.
# Módulos internos da aplicação.
from utils.db import db
from models.base_model import BaseModel
# Biblioteca padrão.
from datetime import datetime as dt

# Define a entidade Users persistida no banco de dados.
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
    # Nome do arquivo privado da assinatura padrão cadastrada para o usuário.
    assinatura_cadastrada = db.Column(db.String)
    # Identidade visual. Valores light/dark legados continuam aceitos na API
    # e são migrados pelo frontend para TMHub + modo de luminosidade.
    tema = db.Column(db.String(24), default="tmhub")
    modo_tema = db.Column(db.String(5), default="light")
    # Camada visual opcional. Mantém o TMHub fluido em máquinas mais simples.
    particulas_ativas = db.Column(db.Boolean, nullable=False, default=True)
    # Liberação administrativa para as identidades visuais extras. A edição
    # é deliberadamente feita no banco enquanto o catálogo está em testes.
    temas_extras_liberados = db.Column(db.Boolean, nullable=False, default=False)
    # Código do adorno de foto equipado pelo marketplace. O item comprado
    # continua sendo a fonte de verdade da posse.
    adorno_foto = db.Column(db.String(80), nullable=True)
    # Skin visual do modelo 3D do Timo. ``default`` usa o acabamento branco
    # canônico; as demais opções são liberadas pelo Marketplace.
    timo_skin = db.Column(db.String(80), nullable=False, default="default")
    timo_ativo = db.Column(db.Boolean, nullable=False, default=False)
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
