# Modelo de dados de colaboradores.
# Módulos internos da aplicação.
from utils.db import db
from models.base_model import BaseModel
from models.empresas import Company
# Biblioteca padrão.
from datetime import datetime as dt

# Define a entidade Employees persistida no banco de dados.
class Employees(BaseModel):
    __tablename__ = "colaboradores"

    # O id mantém os relacionamentos internos atuais. A importação usa a
    # matrícula em conjunto com a empresa para localizar o colaborador.
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    matricula = db.Column(db.Integer, nullable=False, index=True)
    cpf = db.Column(db.String(20), index=True)
    nome = db.Column(db.String)
    data_admissao = db.Column(db.DateTime, default=dt.now())
    cargo = db.Column(db.Integer)
    carga_horaria  =  db.Column(db.Integer)
    # A coluna ja e preenchida pela importacao de colaboradores e e usada
    # somente como base da provisao no Controle de Rescisoes.
    salario = db.Column(db.Numeric(14, 2))
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id", ondelete="RESTRICT"), index=True)

    # Controle de PCD (Pessoa com Deficiência)
    pcd = db.Column(db.Boolean, nullable=False, default=False)
    type_pcd = db.Column(db.String)
    obs_pcd = db.Column(db.String)

    centro_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "centro_de_custo.id",
            ondelete="SET NULL"
        )
    )
    empresa = db.relationship(Company)
    
    situacao = db.Column(
        db.Integer,
        db.ForeignKey(
            "situacoes.id",
            ondelete="SET NULL"
        ),
    )

    __table_args__ = (
        db.UniqueConstraint("empresa_id", "matricula", name="uq_colaborador_empresa_matricula"),
    )

    # Credencial independente para o TM Ops. Estes campos nunca compartilham a
    # senha usada pelos demais módulos do TM Hub.
    tm_ops_password_hash = db.Column(db.String(255), nullable=True)
    tm_ops_ativo = db.Column(db.Boolean, nullable=False, default=False, index=True)
    tm_ops_primeiro_acesso = db.Column(db.Boolean, nullable=False, default=True)
    tm_ops_ultimo_acesso = db.Column(db.DateTime(timezone=True))
    tm_ops_perfil = db.Column(db.String(30), nullable=False, default="executor")
    tm_ops_token_version = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        payload = super().to_dict()
        for field in (
            "tm_ops_password_hash",
            "tm_ops_ativo",
            "tm_ops_primeiro_acesso",
            "tm_ops_ultimo_acesso",
            "tm_ops_perfil",
            "tm_ops_token_version",
        ):
            payload.pop(field, None)
        return payload
