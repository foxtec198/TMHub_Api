from datetime import datetime as dt

from models.base_model import BaseModel
from utils.db import db


class AbsenceControl(BaseModel):
    __tablename__ = "controle_faltas"

    id = db.Column(db.Integer, primary_key=True)
    requisicao_id = db.Column(db.Integer, db.ForeignKey("rp_requisicoes.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id", ondelete="SET NULL"), index=True)
    colaborador_nome = db.Column(db.String(255), nullable=False, default="Colaborador não encontrado")
    colaborador_matricula = db.Column(db.String(50))
    centro_custo_id = db.Column(db.Integer, db.ForeignKey("centro_de_custo.id", ondelete="RESTRICT"), nullable=False, index=True)
    supervisor_id = db.Column(db.Integer, db.ForeignKey("supervisores.id", ondelete="RESTRICT"), nullable=False, index=True)
    motivo = db.Column(db.String(100), nullable=False)
    data_falta = db.Column(db.DateTime(timezone=True), nullable=False)
    prazo_atestado = db.Column(db.DateTime(timezone=True), index=True)
    classificacao = db.Column(db.String(30), nullable=False, default="em_analise", index=True)
    status = db.Column(db.String(20), nullable=False, default="pendente", index=True)
    observacao = db.Column(db.Text)
    tratado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"), index=True)
    tratado_em = db.Column(db.DateTime(timezone=True))
    automatizado_em = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now, onupdate=dt.now)
