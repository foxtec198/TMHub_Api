# =============================== Utils
from utils.db import db

# =============================== Models
from models.base_model import BaseModel


# Define os anexos dos chamados
class TicketAttachment(BaseModel):
    __tablename__ = "tc_anexos"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(
        db.Integer,
        db.ForeignKey("tc_historico.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    comentario_id = db.Column(
        db.Integer,
        db.ForeignKey("tc_comentarios.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    arquivo = db.Column(db.String(255), nullable=False)
    tamanho = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.String(100), nullable=False)
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)

    # Relationships
    ticket = db.relationship("Ticket", foreign_keys=[ticket_id])
    comentario = db.relationship("TicketComment", foreign_keys=[comentario_id])
    criador = db.relationship("Users", foreign_keys=[created_by])
