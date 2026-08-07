from models.base_model import BaseModel
from utils.db import db


class DisciplinaryMeasure(BaseModel):
    __tablename__ = "medidas_disciplinares"
    __table_args__ = (
        db.CheckConstraint(
            "tipo IN ('advertencia', 'suspensao')",
            name="ck_medidas_disciplinares_tipo",
        ),
        db.CheckConstraint(
            "quantidade_dias IS NULL OR quantidade_dias > 0",
            name="ck_medidas_disciplinares_dias",
        ),
    )

    id = db.Column(db.BigInteger, primary_key=True)
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tipo = db.Column(db.String(20), nullable=False, index=True)
    motivo = db.Column(db.String(40), nullable=False, index=True)
    motivo_detalhe = db.Column(db.String(255))
    reincidencia = db.Column(db.Boolean)
    data_medida = db.Column(db.Date, nullable=False, index=True)
    quantidade_dias = db.Column(db.Integer)
    observacao = db.Column(db.Text)
    # Snapshot histórico: mudanças futuras no contrato/supervisor não alteram o registro.
    supervisor_id = db.Column(
        db.Integer,
        db.ForeignKey("supervisores.id", ondelete="SET NULL"),
        index=True,
    )
    supervisor_nome = db.Column(db.String(255), nullable=False, index=True)

    # O fingerprint identifica a mesma medida em lançamentos manuais e importações.
    fingerprint = db.Column(db.String(64), nullable=False, unique=True, index=True)
    origem = db.Column(db.String(20), nullable=False, default="manual")
    arquivo_origem = db.Column(db.String(255))
    linha_origem = db.Column(db.Integer)

    criado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    atualizado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
    )
    criado_em = db.Column(
        db.DateTime(timezone=True), server_default=db.func.now(), nullable=False
    )
    atualizado_em = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )
    colaborador = db.relationship("Employees", lazy="joined")
    criado_por = db.relationship("Users", foreign_keys=[criado_por_usuario_id])
    atualizado_por = db.relationship("Users", foreign_keys=[atualizado_por_usuario_id])
