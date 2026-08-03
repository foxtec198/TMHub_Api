from datetime import datetime as dt

from utils.db import db


class ProjectCardFile(db.Model):
    __tablename__ = "pj_card_file"

    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey("pj_card.id", ondelete="CASCADE"), nullable=False, index=True)
    enviado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"), index=True)
    nome_original = db.Column(db.String(255), nullable=False)
    caminho_arquivo = db.Column(db.String(255), nullable=False, unique=True)
    mime_type = db.Column(db.String(120))
    tamanho_bytes = db.Column(db.BigInteger, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now, index=True)
