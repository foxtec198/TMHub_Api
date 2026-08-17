# Modelo de dados de histórico de chamados.
# Módulos internos da aplicação.
from models.base_model import BaseModel
from utils.db import db


# Define a entidade Ticket persistida no banco de dados.
class Ticket(BaseModel):
    __tablename__ = "tc_historico"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(180), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="ABERTO", index=True)
    observacao = db.Column(db.Text, nullable=False)
    motivo_id = db.Column(
        db.Integer,
        db.ForeignKey("tc_motivos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    updated_by = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_by = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    responsible_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filial_id = db.Column(
        db.Integer,
        db.ForeignKey("filiais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    motivo = db.relationship("TicketReason", foreign_keys=[motivo_id])
    criador = db.relationship("Users", foreign_keys=[created_by])
    responsavel = db.relationship("Users", foreign_keys=[responsible_id])
    resolvido_por = db.relationship("Users", foreign_keys=[resolved_by])
    filial = db.relationship("Branch", foreign_keys=[filial_id])
