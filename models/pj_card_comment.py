# Modelo de dados de comentários de cards.
# Biblioteca padrão.
from datetime import datetime as dt

# Módulos internos da aplicação.
from utils.db import db


# Define a entidade ProjectCardComment persistida no banco de dados.
class ProjectCardComment(db.Model):
    __tablename__ = "pj_card_comment"

    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey("pj_card.id", ondelete="CASCADE"), nullable=False, index=True)
    autor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"), index=True)
    conteudo = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now, onupdate=dt.now)
