# Modelo de dados de rescisões.
# Biblioteca padrão.
from datetime import datetime as dt

# Módulos internos da aplicação.
from models.base_model import BaseModel
from utils.db import db


# Define a entidade Termination persistida no banco de dados.
class Termination(BaseModel):
    __tablename__ = "rh_rescisoes"
    __table_args__ = (
        db.UniqueConstraint(
            "matricula",
            "data_demissao",
            name="uq_rh_rescisoes_matricula_demissao",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    matricula = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.matricula", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    motivo_rescisao = db.Column(db.String(500), nullable=False)
    data_admissao = db.Column(db.Date, nullable=False)

    aviso = db.Column(db.String(50))
    data_demissao = db.Column(db.Date, nullable=False, index=True)
    saldo_fgts = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    proventos = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    descontos = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    liquido = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    fgts_rescisorio = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    arquivo_origem = db.Column(db.String(255))
    importado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        index=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=dt.now,
        onupdate=dt.now,
    )
