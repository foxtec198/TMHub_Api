# Modelo de dados de indicadores de ponto 48h.
# Biblioteca padrão.
from datetime import datetime as dt

# Módulos internos da aplicação.
from models.base_model import BaseModel
from utils.db import db


# Define a entidade Ponto48Import persistida no banco de dados.
class Ponto48Import(BaseModel):
    __tablename__ = "pt48_importacoes"

    id = db.Column(db.Integer, primary_key=True)
    periodo_inicio = db.Column(db.Date, nullable=False, index=True)
    periodo_fim = db.Column(db.Date, nullable=False, index=True)
    arquivo_absenteismo = db.Column(db.String(255), nullable=False)
    arquivo_horas_extras = db.Column(db.String(255), nullable=False)
    criado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=dt.now)


# Define a entidade Ponto48Absenteismo persistida no banco de dados.
class Ponto48Absenteismo(BaseModel):
    __tablename__ = "pt48_absenteismo"

    id = db.Column(db.Integer, primary_key=True)
    importacao_id = db.Column(
        db.Integer,
        db.ForeignKey("pt48_importacoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nome_colaborador = db.Column(db.String(255), nullable=False)
    nome_normalizado = db.Column(db.String(255), nullable=False, index=True)
    match_status = db.Column(db.String(20), nullable=False, default="unmatched")
    previsto_minutos = db.Column(db.Integer, nullable=False, default=0)
    ausencia_minutos = db.Column(db.Integer, nullable=False, default=0)
    presenca_minutos = db.Column(db.Integer, nullable=False, default=0)
    abs_percentual = db.Column(db.Numeric(7, 2), nullable=False, default=0)


# Define a entidade Ponto48HorasExtras persistida no banco de dados.
class Ponto48HorasExtras(BaseModel):
    __tablename__ = "pt48_horas_extras"

    id = db.Column(db.Integer, primary_key=True)
    importacao_id = db.Column(
        db.Integer,
        db.ForeignKey("pt48_importacoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nome_colaborador = db.Column(db.String(255), nullable=False)
    nome_normalizado = db.Column(db.String(255), nullable=False, index=True)
    match_status = db.Column(db.String(20), nullable=False, default="unmatched")
    data = db.Column(db.Date, nullable=False, index=True)
    entrada_1 = db.Column(db.String(5))
    saida_1 = db.Column(db.String(5))
    entrada_2 = db.Column(db.String(5))
    saida_2 = db.Column(db.String(5))
    entrada_3 = db.Column(db.String(5))
    saida_3 = db.Column(db.String(5))
    horas_normais_minutos = db.Column(db.Integer, nullable=False, default=0)
    horas_extras_minutos = db.Column(db.Integer, nullable=False, default=0)
    motivo = db.Column(db.String(255))
    quantidade_batidas = db.Column(db.Integer, nullable=False, default=0)
    batida_impar = db.Column(db.Boolean, nullable=False, default=False)
    batida_irregular = db.Column(db.Boolean, nullable=False, default=False)
    irregularidade = db.Column(db.String(500))


# Define a entidade Ponto48AjusteImport persistida no banco de dados.
class Ponto48AjusteImport(BaseModel):
    __tablename__ = "pt48_ajuste_importacoes"

    id = db.Column(db.Integer, primary_key=True)
    periodo_inicio = db.Column(db.Date, nullable=False, index=True)
    periodo_fim = db.Column(db.Date, nullable=False, index=True)
    arquivo_ajustes = db.Column(db.String(255), nullable=False)
    criado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=dt.now)


# Define a entidade Ponto48Ajuste persistida no banco de dados.
class Ponto48Ajuste(BaseModel):
    __tablename__ = "pt48_ajustes"

    id = db.Column(db.Integer, primary_key=True)
    importacao_id = db.Column(
        db.Integer,
        db.ForeignKey("pt48_ajuste_importacoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nome_colaborador = db.Column(db.String(255), nullable=False)
    nome_normalizado = db.Column(db.String(255), nullable=False, index=True)
    match_status = db.Column(db.String(20), nullable=False, default="unmatched")
    data = db.Column(db.Date, nullable=False, index=True)
    entrada_1 = db.Column(db.String(5))
    saida_1 = db.Column(db.String(5))
    entrada_2 = db.Column(db.String(5))
    saida_2 = db.Column(db.String(5))
    entrada_3 = db.Column(db.String(5))
    saida_3 = db.Column(db.String(5))
    quantidade_batidas = db.Column(db.Integer, nullable=False, default=0)
    batida_impar = db.Column(db.Boolean, nullable=False, default=False)
    ajustado_por = db.Column(db.String(255))
    alterado_em = db.Column(db.DateTime)
    solicitado_em = db.Column(db.DateTime)
    motivo = db.Column(db.String(255))
    solicitacao = db.Column(db.Boolean, nullable=False, default=False)


# Define a entidade Ponto48EspelhoImport persistida no banco de dados.
class Ponto48EspelhoImport(BaseModel):
    __tablename__ = "pt48_espelho_importacoes"

    id = db.Column(db.Integer, primary_key=True)
    periodo_inicio = db.Column(db.Date, nullable=False, index=True)
    periodo_fim = db.Column(db.Date, nullable=False, index=True)
    arquivo_espelho = db.Column(db.String(255), nullable=False)
    criado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=dt.now)


# Define a entidade Ponto48Espelho persistida no banco de dados.
class Ponto48Espelho(BaseModel):
    __tablename__ = "pt48_espelho_ponto"

    id = db.Column(db.Integer, primary_key=True)
    importacao_id = db.Column(
        db.Integer,
        db.ForeignKey("pt48_espelho_importacoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nome_colaborador = db.Column(db.String(255), nullable=False)
    nome_normalizado = db.Column(db.String(255), nullable=False, index=True)
    match_status = db.Column(db.String(20), nullable=False, default="unmatched")
    data = db.Column(db.Date, nullable=False, index=True)
    entrada_1 = db.Column(db.String(5))
    saida_1 = db.Column(db.String(5))
    entrada_2 = db.Column(db.String(5))
    saida_2 = db.Column(db.String(5))
    entrada_3 = db.Column(db.String(5))
    saida_3 = db.Column(db.String(5))
    quantidade_batidas = db.Column(db.Integer, nullable=False, default=0)
    batida_impar = db.Column(db.Boolean, nullable=False, default=False)
    credito_minutos = db.Column(db.Integer, nullable=False, default=0)
    debito_minutos = db.Column(db.Integer, nullable=False, default=0)
    intervalo_minutos = db.Column(db.Integer, nullable=False, default=0)
    horas_normais_minutos = db.Column(db.Integer, nullable=False, default=0)
    horas_extras_1_minutos = db.Column(db.Integer, nullable=False, default=0)
    horas_extras_2_minutos = db.Column(db.Integer, nullable=False, default=0)
    adicional_noturno_minutos = db.Column(db.Integer, nullable=False, default=0)
    saldo_minutos = db.Column(db.Integer, nullable=False, default=0)
    motivo = db.Column(db.Text)
