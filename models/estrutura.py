from utils.db import db
from models.base_model import BaseModel


class StructureLocation(BaseModel):
    __tablename__ = "estrutura_locais"

    id = db.Column(db.Integer, primary_key=True)
    centro_custo_id = db.Column(
        db.Integer,
        db.ForeignKey("centro_de_custo.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome = db.Column(db.String(160), nullable=False)
    descricao = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)


class StructureAsset(BaseModel):
    __tablename__ = "estrutura_ativos"

    id = db.Column(db.Integer, primary_key=True)
    centro_custo_id = db.Column(
        db.Integer,
        db.ForeignKey("centro_de_custo.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    local_id = db.Column(
        db.Integer,
        db.ForeignKey("estrutura_locais.id", ondelete="SET NULL"),
        index=True,
    )
    nome = db.Column(db.String(160), nullable=False)
    categoria = db.Column(db.String(80), nullable=False)
    patrimonio = db.Column(db.String(50), nullable=False, unique=True, index=True)
    descricao = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
