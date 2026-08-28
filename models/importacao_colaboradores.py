"""Histórico auditável das importações de colaboradores."""

from utils.db import db
from models.base_model import BaseModel


class CollaboratorImportLog(BaseModel):
    __tablename__ = "importacao_colaboradores_historico"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    origem = db.Column(db.String(20), nullable=False, index=True)
    empresa_id = db.Column(
        db.Integer,
        db.ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    empresa_nome = db.Column(db.String(150), nullable=False)
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    usuario_nome = db.Column(db.String(150), nullable=True)
    arquivo = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="queued", index=True)
    fase = db.Column(db.String(30), nullable=False, default="preparando")
    total = db.Column(db.Integer, nullable=False, default=0)
    processados = db.Column(db.Integer, nullable=False, default=0)
    colaboradores_criados = db.Column(db.Integer, nullable=False, default=0)
    colaboradores_atualizados = db.Column(db.Integer, nullable=False, default=0)
    colaboradores_ignorados = db.Column(db.Integer, nullable=False, default=0)
    cargos_criados = db.Column(db.Integer, nullable=False, default=0)
    registros_invalidos = db.Column(db.Integer, nullable=False, default=0)
    duplicidades = db.Column(db.Integer, nullable=False, default=0)
    erro = db.Column(db.Text, nullable=True)
    iniciado_em = db.Column(
        db.DateTime(timezone=True), server_default=db.func.now(), nullable=False, index=True
    )
    finalizado_em = db.Column(db.DateTime(timezone=True), nullable=True)
    atualizado_em = db.Column(
        db.DateTime(timezone=True), server_default=db.func.now(), nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "origem": self.origem,
            "empresa_id": self.empresa_id,
            "empresa_nome": self.empresa_nome,
            "usuario_id": self.usuario_id,
            "usuario_nome": self.usuario_nome,
            "arquivo": self.arquivo,
            "status": self.status,
            "fase": self.fase,
            "total": self.total,
            "processados": self.processados,
            "colaboradores_criados": self.colaboradores_criados,
            "colaboradores_atualizados": self.colaboradores_atualizados,
            "colaboradores_ignorados": self.colaboradores_ignorados,
            "cargos_criados": self.cargos_criados,
            "registros_invalidos": self.registros_invalidos,
            "duplicidades": self.duplicidades,
            "erro": self.erro,
            "iniciado_em": self.iniciado_em.isoformat() if self.iniciado_em else None,
            "finalizado_em": self.finalizado_em.isoformat() if self.finalizado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }
