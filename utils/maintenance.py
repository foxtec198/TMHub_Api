"""Controle global de manutenção do TMHub."""

from os import getenv

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from utils.db import db


def _environment_default():
    """Fallback para inicialização antes da tabela existir.

    A configuração persistida no banco prevalece. O padrão agora é operação
    liberada, para impedir uma nova manutenção acidental em um deploy limpo.
    """
    return getenv("MAINTENANCE_MODE", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def maintenance_mode_enabled():
    """Retorna o estado persistido; ambiente é somente fallback técnico."""
    try:
        value = db.session.execute(
            text("SELECT manutencao_ativa FROM configuracoes_sistema WHERE id = 1")
        ).scalar_one_or_none()
        return _environment_default() if value is None else bool(value)
    except SQLAlchemyError:
        return _environment_default()


def update_maintenance_mode(active, user_id):
    """Persiste a alteração global feita por um administrador."""
    db.session.execute(
        text(
            "INSERT INTO configuracoes_sistema "
            "(id, manutencao_ativa, atualizado_em, atualizado_por_usuario_id) "
            "VALUES (1, :active, NOW(), :user_id) "
            "ON CONFLICT (id) DO UPDATE SET "
            "manutencao_ativa = EXCLUDED.manutencao_ativa, "
            "atualizado_em = EXCLUDED.atualizado_em, "
            "atualizado_por_usuario_id = EXCLUDED.atualizado_por_usuario_id"
        ),
        {"active": bool(active), "user_id": user_id},
    )
    db.session.commit()
