# Modelo de dados de requisições de reposição.
# Módulos internos da aplicação.
from models.base_model import BaseModel
# Biblioteca padrão.
from datetime import datetime as dt
# Módulos internos da aplicação.
from utils.db import db

# Define a entidade Requisicao persistida no banco de dados.
class Requisicao(BaseModel):
    __tablename__ = "rp_requisicoes"

    id = db.Column(db.Integer, primary_key=True)
    reserva_id = db.Column(db.Integer, nullable=False)
    # Colaborador que realizou uma cobertura fora das reservas técnicas.
    cobertura_colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="SET NULL"),
        index=True,
    )
    ausente_id = db.Column(db.Integer, nullable=False)
    cc = db.Column(db.Integer, nullable=True)
    # Cadastro legado: preservado somente para leitura de requisições antigas.
    supervisor_id = db.Column(db.Integer, nullable=True)
    # Novo vínculo oficial com o usuário que possui role SUPERVISOR.
    supervisor_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    warning = db.Column(db.Boolean, default=False)
    # Snapshot do adicional para preservar o valor válido na data do lançamento.
    adicional_tipo = db.Column(db.String(100))
    adicional_valor_diaria = db.Column(db.Numeric(12, 2))
    # Identifica a ausência operacional criada quando uma cobertura desloca
    # um colaborador de um cargo de menor valor.
    requisicao_origem_id = db.Column(
        db.Integer,
        db.ForeignKey("rp_requisicoes.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    # Toda requisição precisa informar de onde nasceu. O default do ORM e do
    # banco protege fluxos antigos que não enviam essa informação explicitamente.
    origem = db.Column(
        db.String(30),
        nullable=False,
        default="requisicao",
        server_default="requisicao",
        index=True,
    )
    motivo = db.Column(db.String)
    obs = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=dt.now)
    opened_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    status = db.Column(db.String, default="pending")
