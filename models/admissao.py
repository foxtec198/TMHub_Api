from utils.db import db
from models.base_model import BaseModel
from datetime import datetime as dt

class WorkSchedule(BaseModel):
    """Catálogo deduplicado de jornadas digitadas pelos usuários."""
    __tablename__ = "ad_horarios_trabalho"

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    descricao_normalizada = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=dt.now)

class InterviewHistory(BaseModel):
    """Histórico consolidado de entrevistas importadas e vagas concluídas."""
    __tablename__ = "ad_entrevistas_historico"

    id = db.Column(db.Integer, primary_key=True)
    vaga_id = db.Column(db.Integer, db.ForeignKey("ad_vagas.id", ondelete="SET NULL"), index=True)
    colaborador_saida_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    centro_custo_id = db.Column(
        db.Integer,
        db.ForeignKey("centro_de_custo.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    responsavel_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="RESTRICT"),
        index=True,
    )
    candidato_colaborador_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id", ondelete="SET NULL"), index=True)
    cargo_id = db.Column(db.Integer, db.ForeignKey("cargos.id", ondelete="SET NULL"), index=True)
    supervisor_id = db.Column(db.Integer, db.ForeignKey("supervisores.id", ondelete="SET NULL"), index=True)
    # O candidato pode ainda não existir na base; nesse caso preservamos seu nome em texto.
    candidato_nome = db.Column(db.String(255))
    entrevista_data = db.Column(db.Date)
    entrevista_data_original = db.Column(db.String(50))
    inicio_data = db.Column(db.Date)
    inicio_data_original = db.Column(db.String(50))
    funcao = db.Column(db.String(150))
    status = db.Column(db.String(100), nullable=False, default="SEM STATUS")
    observacoes = db.Column(db.Text)
    telefone = db.Column(db.String(50))
    substituicao = db.Column(db.Text)
    supervisor = db.Column(db.String(150))
    origem_aba = db.Column(db.String(100), nullable=False)
    origem_linha = db.Column(db.Integer, nullable=False)
    aviso_em = db.Column(db.DateTime(timezone=True))
    primeira_acao_em = db.Column(db.DateTime(timezone=True))
    entrevista_em_sla = db.Column(db.DateTime(timezone=True))
    concluido_em = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime, nullable=False, default=dt.now)

    __table_args__ = (
        db.UniqueConstraint("origem_aba", "origem_linha", name="uq_ad_entrevistas_origem"),
        db.CheckConstraint(
            "candidato_colaborador_id IS NULL OR status IN ('APROVADO', 'CONTRATADO')",
            name="ck_ad_entrevistas_candidato_vinculavel",
        ),
    )

class VacancyEvent(BaseModel):
    """Linha do tempo auditável de cada mudança de status da vaga."""
    __tablename__ = "ad_vagas_eventos"

    id = db.Column(db.Integer, primary_key=True)
    vaga_id = db.Column(db.Integer, db.ForeignKey("ad_vagas.id", ondelete="CASCADE"), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"), index=True)
    ocorrido_em = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=dt.now)


class VacancyCandidateHistory(BaseModel):
    """Preserva cada candidato considerado e seu resultado dentro da vaga."""
    __tablename__ = "ad_vagas_candidatos_historico"

    id = db.Column(db.Integer, primary_key=True)
    vaga_id = db.Column(
        db.Integer,
        db.ForeignKey("ad_vagas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidato_nome = db.Column(db.String(255), nullable=False)
    telefone = db.Column(db.String(50))
    resultado = db.Column(db.String(30), nullable=False)
    observacao = db.Column(db.Text)
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="SET NULL"),
        index=True,
    )
    registrado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        index=True,
    )
    ocorrido_em = db.Column(db.DateTime(timezone=True), nullable=False, default=dt.now)
    created_at = db.Column(db.DateTime(timezone=True), default=dt.now)

class Vacancy(BaseModel):
    """Vaga operacional vinculada ao colaborador que será substituído."""
    __tablename__ = "ad_vagas"

    id = db.Column(db.Integer, primary_key=True)

    # Dados profissionais são derivados do colaborador, sem duplicação na vaga.
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Nullable preserva vagas legadas; novas vagas exigem o supervisor no serviço.
    supervisor_id = db.Column(
        db.Integer,
        db.ForeignKey("supervisores.id", ondelete="RESTRICT"),
        index=True,
    )
    # Responsável é o usuário do TMHub; supervisor é uma entidade operacional separada.
    responsavel_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="RESTRICT"),
        index=True,
    )

    # Preenchimento manual
    horario_trabalho_id = db.Column(
        db.Integer,
        db.ForeignKey("ad_horarios_trabalho.id", ondelete="RESTRICT"),
        index=True,
    )
    motivo_saida = db.Column(db.String)
    # Nome livre: a pessoa ainda não existe na tabela de colaboradores.
    colaborador_entrada = db.Column(db.String)
    # Nome e telefone permanecem livres até a conclusão; somente então o ID é obrigatório.
    telefone_colaborador_entrada = db.Column(db.String(50))
    # Dados estruturados preenchidos na conclusão da vaga.
    colaborador_entrada_id = db.Column(
        db.Integer,
        db.ForeignKey("colaboradores.id", ondelete="RESTRICT"),
        index=True,
    )
    data_inicio = db.Column(db.DateTime(timezone=True))
    observacao_conclusao = db.Column(db.Text)
    concluido_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="RESTRICT"),
        index=True,
    )
    concluido_em = db.Column(db.DateTime(timezone=True))
    # Dia em que o supervisor avisou a vaga ou encaminhou o currículo.
    data_aviso = db.Column(db.Date)
    aviso_em = db.Column(db.DateTime(timezone=True))

    # Status da vaga
    status = db.Column(db.String, default="aberta")

    # Dados obrigatórios ao mover a vaga para "Entrevista"
    entrevistador = db.Column(db.String)
    entrevista_data = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=dt.now)
    updated_at = db.Column(db.DateTime, default=dt.now, onupdate=dt.now)
