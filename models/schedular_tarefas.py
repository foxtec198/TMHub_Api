from datetime import datetime as dt

from models.base_model import BaseModel
from utils.db import db


class SchedularTask(BaseModel):
    __tablename__ = "schedular_tarefas"

    id = db.Column(db.Integer, primary_key=True)
    rotina_id = db.Column(db.Integer, db.ForeignKey("schedular_rotinas.id", ondelete="CASCADE"), nullable=False, index=True)
    rotina_estrutura_id = db.Column(db.Integer, db.ForeignKey("schedular_rotina_estruturas.id", ondelete="RESTRICT"), index=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id", ondelete="SET NULL"), nullable=False, index=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey("schedular_checklists.id", ondelete="SET NULL"), nullable=True)
    centro_custo_id = db.Column(db.Integer, db.ForeignKey("centro_de_custo.id", ondelete="SET NULL"), nullable=True)
    local_id = db.Column(db.Integer, db.ForeignKey("estrutura_locais.id", ondelete="SET NULL"), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="aberta", index=True)
    origem = db.Column(db.String(30), nullable=False, default="rotina", index=True)
    agendada_para = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    prazo_em = db.Column(db.DateTime(timezone=True), index=True)
    estimativa_minutos = db.Column(db.Integer)
    ocorrencia_em = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    iniciada_em = db.Column(db.DateTime(timezone=True))
    pausada_em = db.Column(db.DateTime(timezone=True))
    cancelada_em = db.Column(db.DateTime(timezone=True))
    concluida_em = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)

    __table_args__ = (db.UniqueConstraint("rotina_estrutura_id", "ocorrencia_em", name="uq_schedular_tarefa_ocorrencia"),)


class SchedularTaskResponse(BaseModel):
    __tablename__ = "schedular_tarefa_respostas"
    __table_args__ = (db.UniqueConstraint("tarefa_id", "checklist_item_id", name="uq_schedular_resposta_item"),)

    id = db.Column(db.Integer, primary_key=True)
    tarefa_id = db.Column(db.Integer, db.ForeignKey("schedular_tarefas.id", ondelete="CASCADE"), nullable=False, index=True)
    checklist_item_id = db.Column(db.Integer, db.ForeignKey("schedular_checklist_itens.id", ondelete="RESTRICT"), nullable=False, index=True)
    valor = db.Column(db.JSON, nullable=False, default=dict)
    respondido_por_colaborador_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id", ondelete="SET NULL"), nullable=True)
    respondido_em = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)


class SchedularTaskEvidence(BaseModel):
    __tablename__ = "schedular_tarefa_evidencias"

    id = db.Column(db.Integer, primary_key=True)
    resposta_id = db.Column(db.Integer, db.ForeignKey("schedular_tarefa_respostas.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = db.Column(db.String(30), nullable=False)
    valor = db.Column(db.Text, nullable=False)
    obrigatoria = db.Column(db.Boolean, nullable=False, default=True)
    coletada_por_colaborador_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id", ondelete="SET NULL"), nullable=True)
    coletada_em = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
