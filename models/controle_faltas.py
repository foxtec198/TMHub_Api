# Modelo de dados de controle de faltas.
# Biblioteca padrão.
from datetime import datetime as dt

# Módulos internos da aplicação.
from models.base_model import BaseModel
from utils.db import db


# Define a entidade AbsenceControl persistida no banco de dados.
class AbsenceControl(BaseModel):
    __tablename__ = "controle_faltas"

    id = db.Column(db.Integer, primary_key=True)
    requisicao_id = db.Column(db.Integer, db.ForeignKey("rp_requisicoes.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id", ondelete="SET NULL"), index=True)
    colaborador_nome = db.Column(db.String(255), nullable=False, default="Colaborador não encontrado")
    colaborador_matricula = db.Column(db.String(50))
    centro_custo_id = db.Column(db.Integer, db.ForeignKey("centro_de_custo.id", ondelete="RESTRICT"), nullable=False, index=True)
    # Mantido apenas como referência do cadastro legado das faltas históricas.
    supervisor_id = db.Column(db.Integer, db.ForeignKey("supervisores.id", ondelete="RESTRICT"), nullable=True, index=True)
    supervisor_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    motivo = db.Column(db.String(100), nullable=False)
    tipo_ausencia = db.Column(db.String(20), nullable=False, default="integral", index=True)
    quantidade_horas = db.Column(db.Numeric(6, 2))
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
