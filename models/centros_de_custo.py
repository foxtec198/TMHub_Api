# Modelo de dados de centros de custo.
# Módulos internos da aplicação.
from utils.db import db
from models.base_model import BaseModel
from models.empresas import Company

# Define a entidade CostCenters persistida no banco de dados.
class CostCenters(BaseModel):
    __tablename__ = "centro_de_custo"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id", ondelete="RESTRICT"), index=True)
    centro_id = db.Column(db.Integer, nullable=True, index=True)
    nome = db.Column(db.String)
    local = db.Column(db.String)
    departamento = db.Column(db.Integer)
    # Capacidade contratual planejada; ainda não bloqueia movimentações nem
    # admissões, mas fica disponível para as próximas regras operacionais.
    capacidade_pessoas = db.Column(db.Integer, nullable=True)
    # Referência legada ao cadastro anterior de supervisores. Não é mais
    # preenchida por fluxos novos; permanece para exibir registros históricos.
    supervisor_id = db.Column(db.Integer, nullable=True)
    # Fonte oficial do responsável atual do contrato. O usuário precisa ter a
    # role SUPERVISOR e continua submetido ao escopo de filiais.
    supervisor_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cidade_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "cidades.id",
            ondelete="SET NULL"
        )
    )
    valor_diaria_glosa = db.Column(db.Numeric(12, 2), nullable=True)
    filiais = db.relationship("Branch", secondary="filial_centros_custo", back_populates="centros_custo")
    # Import explícito evita que o mapper dependa da ordem em que os módulos
    # são carregados pelo Gunicorn.
    empresa = db.relationship(Company)

    __table_args__ = (
        db.UniqueConstraint("empresa_id", "centro_id", name="uq_centro_empresa_codigo"),
    )


# Define a entidade DepartmentConfiguration persistida no banco de dados.
class DepartmentConfiguration(BaseModel):
    __tablename__ = "configuracoes_departamentos"

    departamento = db.Column(db.Integer, primary_key=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    # Meta de quadro do departamento. A capacidade legada dos centros de
    # custo é preservada apenas para compatibilidade e migração de dados.
    capacidade_pessoas = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )
