# Modelo de dados do controle de exames periódicos.
# Módulos internos da aplicação.
from models.base_model import BaseModel
from utils.db import db


class PeriodicExam(BaseModel):
    """Registra um exame importado e sua tratativa dentro do TM Hub."""

    __tablename__ = "exames_periodicos"

    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    centro_custo_id = db.Column(
        db.Integer,
        db.ForeignKey("centro_de_custo.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    tipo_exame = db.Column(db.String(100), nullable=False)
    data_exame = db.Column(db.Date, nullable=True)
    resultado = db.Column(db.String(100), nullable=True)
    data_vencimento = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="a_vencer", index=True)
    observacao = db.Column(db.String(500), nullable=True)
    concluido_em = db.Column(db.DateTime(timezone=True), nullable=True)
    concluido_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lote_importacao = db.Column(db.String(36), nullable=True, index=True)
    importado_em = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
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

    __table_args__ = (
        db.UniqueConstraint(
            "colaborador_id",
            "tipo_exame",
            "data_vencimento",
            name="uq_exame_periodico_colaborador_tipo_vencimento",
        ),
        db.CheckConstraint(
            "status IN ('a_vencer', 'pendente', 'em_andamento', 'concluido')",
            name="ck_exame_periodico_status",
        ),
    )
