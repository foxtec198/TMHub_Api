# Modelo de dados de checklists agendados.
# Biblioteca padrão.
from datetime import datetime as dt

# Módulos internos da aplicação.
from models.base_model import BaseModel
from utils.db import db


# Define a entidade SchedularChecklist persistida no banco de dados.
class SchedularChecklist(BaseModel):
    __tablename__ = "schedular_checklists"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(160), nullable=False)
    descricao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now, onupdate=dt.now)


# Define a entidade SchedularChecklistItem persistida no banco de dados.
class SchedularChecklistItem(BaseModel):
    __tablename__ = "schedular_checklist_itens"

    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey("schedular_checklists.id", ondelete="CASCADE"), nullable=False, index=True)
    pergunta = db.Column(db.String(500), nullable=False)
    tipo_resposta = db.Column(db.String(30), nullable=False, default="texto")
    obrigatorio = db.Column(db.Boolean, nullable=False, default=False)
    ordem = db.Column(db.Integer, nullable=False, default=0)
    opcoes = db.Column(db.JSON, nullable=False, default=list)
    evidencias = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
