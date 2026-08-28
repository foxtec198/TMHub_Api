# Modelo de dados das avaliações do período de experiência.
from datetime import datetime as dt

from models.base_model import BaseModel
from utils.db import db


class ExperienceEvaluation(BaseModel):
    """Tarefa e formulário de avaliação de um colaborador em experiência."""

    __tablename__ = "avaliacoes_experiencia"
    __table_args__ = (
        db.UniqueConstraint(
            "colaborador_id",
            "data_fim_experiencia",
            name="uq_avaliacao_experiencia_colaborador_periodo",
        ),
        db.CheckConstraint(
            "status IN ('aberta', 'em_preenchimento', 'aguardando_rh', "
            "'concluida', 'atrasada', 'cancelada')",
            name="ck_avaliacoes_experiencia_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    supervisor_id = db.Column(
        db.Integer,
        db.ForeignKey("supervisores.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # Vínculo oficial com o usuário que possui a role SUPERVISOR. O campo
    # supervisor_id permanece somente para compatibilidade com avaliações
    # históricas já gravadas.
    supervisor_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Os dados de identificação, contrato e histórico são consultados nas
    # tabelas existentes para evitar duplicação e inconsistência cadastral.
    data_fim_experiencia = db.Column(db.Date, nullable=False, index=True)
    data_referencia_util = db.Column(db.Date, nullable=False)

    status = db.Column(db.String(30), nullable=False, default="aberta", index=True)
    aberta_em = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    prazo_supervisor_em = db.Column(db.DateTime(timezone=True), nullable=False, index=True)

    # Respostas do supervisor, no formato {competencia: classificacao}.
    competencias = db.Column(db.JSON, nullable=False, default=dict)
    classificacao_perfil = db.Column(db.String(40))
    decisao_supervisor = db.Column(db.String(20))
    observacoes_supervisor = db.Column(db.Text)
    # Assinatura manuscrita em PNG, registrada somente ao concluir a etapa.
    assinatura_supervisor = db.Column(db.Text)
    supervisor_concluido_em = db.Column(db.DateTime(timezone=True))
    supervisor_concluido_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
    )

    # Campos exclusivos do RH.
    decisao_rh = db.Column(db.String(20))
    observacoes_rh = db.Column(db.Text)
    # A assinatura do RH conclui definitivamente a avaliação.
    assinatura_rh = db.Column(db.Text)
    rh_concluido_em = db.Column(db.DateTime(timezone=True))
    rh_concluido_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
    )

    cancelada_em = db.Column(db.DateTime(timezone=True))
    motivo_cancelamento = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=dt.now,
        onupdate=dt.now,
    )

    colaborador = db.relationship("Employees", lazy="joined")
    supervisor = db.relationship("Supervisors", lazy="joined")
    supervisor_usuario = db.relationship(
        "Users",
        foreign_keys=[supervisor_usuario_id],
        lazy="joined",
    )
