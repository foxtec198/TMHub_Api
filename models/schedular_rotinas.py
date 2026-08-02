from datetime import datetime as dt

from models.base_model import BaseModel
from utils.db import db


class SchedularRoutine(BaseModel):
    __tablename__ = "schedular_rotinas"

    id = db.Column(db.Integer, primary_key=True)
    rotina_pai_id = db.Column(
        db.Integer,
        db.ForeignKey("schedular_rotinas.id", ondelete="SET NULL"),
        index=True,
    )
    centro_custo_id = db.Column(db.Integer, db.ForeignKey("centro_de_custo.id", ondelete="CASCADE"), nullable=False, index=True)
    local_id = db.Column(
        db.Integer,
        db.ForeignKey("estrutura_locais.id", ondelete="SET NULL"),
        index=True,
    )
    nome = db.Column(db.String(160), nullable=False)
    descricao = db.Column(db.Text)
    recorrencia = db.Column(db.String(20), nullable=False, default="semanal")
    configuracao = db.Column(db.JSON, nullable=False, default=dict)
    colaborador_responsavel_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id", ondelete="SET NULL"), nullable=True, index=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey("schedular_checklists.id", ondelete="SET NULL"), nullable=True, index=True)
    recorrencia_tipo = db.Column(db.String(20), nullable=False, default="semanal")
    intervalo_horas = db.Column(db.Integer)
    estimativa_minutos = db.Column(db.Integer, nullable=False, default=15)
    # Anchor chosen by the operator. It never drifts with the worker execution time.
    inicio_recorrencia = db.Column(db.DateTime(timezone=True), index=True)
    proxima_execucao = db.Column(db.DateTime(timezone=True), index=True)
    ativa = db.Column(db.Boolean, nullable=False, default=True, index=True)
    criado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now, onupdate=dt.now)


class SchedularRoutineStructure(BaseModel):
    __tablename__ = "schedular_rotina_estruturas"
    __table_args__ = (db.UniqueConstraint("rotina_id", "estrutura_id", name="uq_schedular_rotina_estrutura"),)

    id = db.Column(db.Integer, primary_key=True)
    rotina_id = db.Column(db.Integer, db.ForeignKey("schedular_rotinas.id", ondelete="CASCADE"), nullable=False, index=True)
    estrutura_id = db.Column(
        db.Integer,
        db.ForeignKey("estrutura_locais.id", ondelete="SET NULL"),
        index=True,
    )
    origem = db.Column(db.String(30), nullable=False, default="rotina")
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
