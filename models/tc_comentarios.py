from models.base_model import BaseModel
from utils.db import db


class TicketComment(BaseModel):
    __tablename__ = "tc_comentarios"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(180), nullable=True)
    descricao = db.Column(db.Text, nullable=False)
    descricao_origem = db.Column(db.Text, nullable=True)
    arquivo = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="ENVIADO")
    ticket_id = db.Column(
        db.Integer,
        db.ForeignKey("tc_historico.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
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
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)
    read_by = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )

    ticket = db.relationship("Ticket", backref=db.backref("comentarios", cascade="all, delete-orphan"))
    criador = db.relationship("Users", foreign_keys=[created_by])
