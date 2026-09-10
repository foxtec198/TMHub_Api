# Modelo de dados de motivos de chamados.
# Módulos internos da aplicação.
from models.base_model import BaseModel
from models.setores import Sector
from utils.db import db


# Define a entidade TicketReason persistida no banco de dados.
class TicketReason(BaseModel):
    __tablename__ = "tc_motivos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True, index=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )
    # Setor responsável por este motivo
    setor_id = db.Column(
        db.Integer,
        db.ForeignKey("setores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Relationship com setor
    setor = db.relationship("Sector", foreign_keys=[setor_id])
