# Modelo de dados de centros de custo.
# Módulos internos da aplicação.
from utils.db import db
from models.base_model import BaseModel

# Define a entidade CostCenters persistida no banco de dados.
class CostCenters(BaseModel):
    __tablename__ = "centro_de_custo"

    id = db.Column(db.Integer, primary_key=True)
    local = db.Column(db.String)
    departamento = db.Column(db.Integer)
    # Capacidade contratual planejada; ainda não bloqueia movimentações nem
    # admissões, mas fica disponível para as próximas regras operacionais.
    capacidade_pessoas = db.Column(db.Integer, nullable=True)
    supervisor_id = db.Column(db.Integer)
    cidade_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "cidades.id",
            ondelete="SET NULL"
        )
    )
    valor_diaria_glosa = db.Column(db.Numeric(12, 2), nullable=True)
    filiais = db.relationship("Branch", secondary="filial_centros_custo", back_populates="centros_custo")


# Define a entidade DepartmentConfiguration persistida no banco de dados.
class DepartmentConfiguration(BaseModel):
    __tablename__ = "configuracoes_departamentos"

    departamento = db.Column(db.Integer, primary_key=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )
