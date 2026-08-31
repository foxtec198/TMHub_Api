# Biblioteca padrão.
from datetime import datetime as dt

# Módulos internos da aplicação.
from models.base_model import BaseModel
from models.empresas import Company
from utils.db import db


class DreImport(BaseModel):
    """Identifica cada arquivo de origem aceito pelo controle DRE."""

    __tablename__ = "dre_importacoes"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(30), nullable=False, index=True)
    competencia = db.Column(db.Date, nullable=False, index=True)
    filial_id = db.Column(
        db.Integer,
        db.ForeignKey("filiais.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # A filial representa o escopo operacional. A empresa identifica quem
    # possui o dado financeiro e impede que matrículas ou departamentos de
    # empresas diferentes sejam consolidados na mesma DRE.
    empresa_id = db.Column(
        db.Integer,
        db.ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    arquivo_original = db.Column(db.String(255), nullable=False)
    arquivo_hash = db.Column(db.String(64), nullable=False, index=True)
    registros_lidos = db.Column(db.Integer, nullable=False, default=0)
    registros_importados = db.Column(db.Integer, nullable=False, default=0)
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    importado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)

    filial = db.relationship("Branch")
    empresa = db.relationship(Company)
    lancamentos = db.relationship(
        "DreEntry",
        cascade="all, delete-orphan",
        passive_deletes=True,
        back_populates="importacao",
    )


class DreEntry(BaseModel):
    """Mantém o dado financeiro normalizado."""

    __tablename__ = "dre_lancamentos"
    __table_args__ = (
        db.UniqueConstraint(
            "importacao_id",
            "chave_origem",
            name="uq_dre_lancamentos_importacao_chave",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    importacao_id = db.Column(
        db.Integer,
        db.ForeignKey("dre_importacoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competencia = db.Column(db.Date, nullable=False, index=True)
    empresa_id = db.Column(
        db.Integer,
        db.ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    departamento = db.Column(db.Integer, nullable=False, index=True)
    centro_custo_id = db.Column(
        db.Integer,
        db.ForeignKey("centro_de_custo.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contrato_codigo = db.Column(db.String(40), nullable=True, index=True)
    categoria = db.Column(db.String(60), nullable=False, index=True)
    valor = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    quantidade = db.Column(db.Numeric(14, 4), nullable=True)
    documento = db.Column(db.String(100), nullable=True)
    descricao = db.Column(db.String(500), nullable=True)
    fornecedor = db.Column(db.String(255), nullable=True)
    ordem_compra = db.Column(db.String(100), nullable=True)
    chave_origem = db.Column(db.String(128), nullable=False)
    # Quando verdadeiro, este lançamento manual substitui o total importado
    # da mesma categoria, departamento e competência no cálculo da DRE.
    substitui_importacao = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )
    criado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=dt.now,
        onupdate=dt.now,
    )

    importacao = db.relationship("DreImport", back_populates="lancamentos")
    empresa = db.relationship(Company)
