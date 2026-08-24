"""Inicialização do schema e migrações legadas sem Alembic.

As migrações deste módulo são aditivas e idempotentes. Elas permanecem no
startup para manter compatibilidade com as instalações atuais da API, mas
ficam isoladas da configuração e das rotas da aplicação Flask.
"""

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from utils.db import db


def _table_columns(table_name):
    return {
        column["name"]
        for column in inspect(db.engine).get_columns(table_name)
    }


def _run_column_migration(table_name, column_name, statements):
    """Executa uma migração apenas quando a coluna ainda não existe."""
    if column_name in _table_columns(table_name):
        return

    try:
        with db.engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
    except SQLAlchemyError:
        # Outro worker pode concluir a mesma alteração entre o inspect e o ALTER.
        if column_name not in _table_columns(table_name):
            raise


def _migrate_user_theme():
    _run_column_migration(
        "usuarios",
        "modo_tema",
        (
            "ALTER TABLE usuarios "
            "ADD COLUMN modo_tema VARCHAR(5) NOT NULL DEFAULT 'light'",
            "UPDATE usuarios SET modo_tema = CASE "
            "WHEN LOWER(tema) = 'dark' THEN 'dark' ELSE 'light' END",
            "UPDATE usuarios SET tema = 'tmhub' "
            "WHERE LOWER(tema) IN ('light', 'dark')",
        ),
    )


def _migrate_timo_user_preference():
    _run_column_migration(
        "usuarios",
        "timo_ativo",
        (
            "ALTER TABLE usuarios "
            "ADD COLUMN timo_ativo BOOLEAN NOT NULL DEFAULT FALSE",
        ),
    )


def _migrate_requisition_origin(table_names):
    if "rp_requisicoes" not in table_names:
        return

    _run_column_migration(
        "rp_requisicoes",
        "origem",
        (
            "ALTER TABLE rp_requisicoes "
            "ADD COLUMN origem VARCHAR(30) NOT NULL DEFAULT 'requisicao'",
            "CREATE INDEX IF NOT EXISTS ix_rp_requisicoes_origem "
            "ON rp_requisicoes (origem)",
            "UPDATE rp_requisicoes requisicao "
            "SET origem = 'controle_faltas' "
            "WHERE EXISTS ("
            "  SELECT 1 FROM rp_timeline timeline "
            "  WHERE timeline.requisicao_id = requisicao.id "
            "  AND timeline.tipo = "
            "'Requisição criada através do Controle de Faltas'"
            ")",
        ),
    )


def _migrate_department_capacity(table_names):
    if "configuracoes_departamentos" not in table_names:
        return

    _run_column_migration(
        "configuracoes_departamentos",
        "capacidade_pessoas",
        (
            "ALTER TABLE configuracoes_departamentos "
            "ADD COLUMN capacidade_pessoas INTEGER",
            "INSERT INTO configuracoes_departamentos "
            "(departamento, ativo, capacidade_pessoas) "
            "SELECT departamento, TRUE, SUM(capacidade_pessoas)::INTEGER "
            "FROM centro_de_custo "
            "WHERE departamento IS NOT NULL "
            "AND capacidade_pessoas IS NOT NULL "
            "GROUP BY departamento "
            "ON CONFLICT (departamento) DO UPDATE SET "
            "capacidade_pessoas = EXCLUDED.capacidade_pessoas "
            "WHERE configuracoes_departamentos.capacidade_pessoas IS NULL",
        ),
    )


def _migrate_timo_configuration(table_names):
    if "timo_configuracoes" not in table_names:
        return

    migrations = (
        ("titulo", "ALTER TABLE timo_configuracoes ADD COLUMN titulo VARCHAR(150)"),
        ("descricao", "ALTER TABLE timo_configuracoes ADD COLUMN descricao TEXT"),
        (
            "personalizado",
            "ALTER TABLE timo_configuracoes ADD COLUMN personalizado "
            "BOOLEAN NOT NULL DEFAULT FALSE",
        ),
    )
    for column_name, statement in migrations:
        _run_column_migration("timo_configuracoes", column_name, (statement,))


def _migrate_floaters():
    migrations = (
        (
            "disponivel",
            "ALTER TABLE volantes ADD COLUMN disponivel "
            "BOOLEAN NOT NULL DEFAULT TRUE",
        ),
        (
            "indisponibilidade_motivo",
            "ALTER TABLE volantes ADD COLUMN indisponibilidade_motivo VARCHAR(12)",
        ),
        (
            "indisponivel_em",
            "ALTER TABLE volantes ADD COLUMN indisponivel_em TIMESTAMP",
        ),
    )
    for column_name, statement in migrations:
        _run_column_migration("volantes", column_name, (statement,))


def _migrate_ticket_branch(table_names):
    if "tc_historico" not in table_names:
        return

    _run_column_migration(
        "tc_historico",
        "filial_id",
        (
            "ALTER TABLE tc_historico ADD COLUMN filial_id INTEGER "
            "REFERENCES filiais(id) ON DELETE SET NULL",
            "CREATE INDEX IF NOT EXISTS ix_tc_historico_filial_id "
            "ON tc_historico (filial_id)",
            "UPDATE tc_historico ticket "
            "SET filial_id = ("
            "  SELECT MIN(link.filial_id) FROM filial_usuarios link "
            "  WHERE link.usuario_id = ticket.created_by"
            ") "
            "WHERE ticket.filial_id IS NULL AND ticket.created_by IS NOT NULL",
        ),
    )


def _migrate_usage_control(table_names):
    """Cria os índices em instalações em que as tabelas foram criadas antes."""
    if "tm_uso_diario" not in table_names or "tm_uso_eventos" not in table_names:
        return
    try:
        with db.engine.begin() as connection:
            connection.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_tm_uso_diario_usuario_dia "
                "ON tm_uso_diario (usuario_id, dia)"
            ))
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_tm_uso_eventos_diario_ocorrido "
                "ON tm_uso_eventos (uso_diario_id, ocorrido_em)"
            ))
    except SQLAlchemyError:
        # A telemetria é complementar e não deve impedir a inicialização.
        return


def initialize_database(app):
    """Cria tabelas ausentes e aplica as migrações aditivas de startup."""
    with app.app_context():
        db.create_all()
        table_names = set(inspect(db.engine).get_table_names())

        _migrate_user_theme()
        _migrate_timo_user_preference()
        _migrate_requisition_origin(table_names)
        _migrate_department_capacity(table_names)
        _migrate_timo_configuration(table_names)
        _migrate_floaters()
        _migrate_ticket_branch(table_names)
        _migrate_usage_control(table_names)
