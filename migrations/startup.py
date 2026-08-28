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

    _run_column_migration(
        "usuarios",
        "particulas_ativas",
        (
            "ALTER TABLE usuarios "
            "ADD COLUMN particulas_ativas BOOLEAN NOT NULL DEFAULT TRUE",
        ),
    )

    _run_column_migration(
        "usuarios",
        "temas_extras_liberados",
        (
            "ALTER TABLE usuarios "
            "ADD COLUMN temas_extras_liberados BOOLEAN NOT NULL DEFAULT FALSE",
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

    # Instalações que já possuíam a coluna antes desta migration podem não ter
    # recebido o default físico. Mantém o banco protegido além do default ORM.
    try:
        with db.engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE rp_requisicoes "
                "ALTER COLUMN origem SET DEFAULT 'requisicao'"
            ))
    except SQLAlchemyError:
        # O default do modelo ainda atende bancos/dialetos que não aceitam a
        # sintaxe acima; a inicialização não deve ficar indisponível por isso.
        pass


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


def _migrate_supervisor_users(table_names):
    """Promove vínculos legados para usuários de forma idempotente.

    O cadastro ``supervisores`` não é removido: ids e nomes antigos ainda são
    necessários para relatórios e timelines já gravados. A partir desta
    alteração, os fluxos novos usam exclusivamente ``usuarios.id``.
    """
    migrations = {
        "supervisores": (
            "usuario_id",
            (
                "ALTER TABLE supervisores ADD COLUMN usuario_id INTEGER "
                "REFERENCES usuarios(id) ON DELETE SET NULL",
                "CREATE INDEX IF NOT EXISTS ix_supervisores_usuario_id "
                "ON supervisores (usuario_id)",
            ),
        ),
        "centro_de_custo": (
            "supervisor_usuario_id",
            (
                "ALTER TABLE centro_de_custo ADD COLUMN supervisor_usuario_id INTEGER "
                "REFERENCES usuarios(id) ON DELETE SET NULL",
                "CREATE INDEX IF NOT EXISTS ix_centro_de_custo_supervisor_usuario_id "
                "ON centro_de_custo (supervisor_usuario_id)",
            ),
        ),
        "rp_requisicoes": (
            "supervisor_usuario_id",
            (
                "ALTER TABLE rp_requisicoes ADD COLUMN supervisor_usuario_id INTEGER "
                "REFERENCES usuarios(id) ON DELETE SET NULL",
                "CREATE INDEX IF NOT EXISTS ix_rp_requisicoes_supervisor_usuario_id "
                "ON rp_requisicoes (supervisor_usuario_id)",
            ),
        ),
        "rp_historico": (
            "supervisor_usuario_id",
            (
                "ALTER TABLE rp_historico ADD COLUMN supervisor_usuario_id INTEGER "
                "REFERENCES usuarios(id) ON DELETE SET NULL",
                "CREATE INDEX IF NOT EXISTS ix_rp_historico_supervisor_usuario_id "
                "ON rp_historico (supervisor_usuario_id)",
            ),
        ),
        "rp_timeline": (
            "supervisor_usuario_id",
            (
                "ALTER TABLE rp_timeline ADD COLUMN supervisor_usuario_id INTEGER "
                "REFERENCES usuarios(id) ON DELETE SET NULL",
                "CREATE INDEX IF NOT EXISTS ix_rp_timeline_supervisor_usuario_id "
                "ON rp_timeline (supervisor_usuario_id)",
            ),
        ),
        "controle_faltas": (
            "supervisor_usuario_id",
            (
                "ALTER TABLE controle_faltas ADD COLUMN supervisor_usuario_id INTEGER "
                "REFERENCES usuarios(id) ON DELETE SET NULL",
                "CREATE INDEX IF NOT EXISTS ix_controle_faltas_supervisor_usuario_id "
                "ON controle_faltas (supervisor_usuario_id)",
            ),
        ),
        "avaliacoes_experiencia": (
            "supervisor_usuario_id",
            (
                "ALTER TABLE avaliacoes_experiencia ADD COLUMN supervisor_usuario_id INTEGER "
                "REFERENCES usuarios(id) ON DELETE SET NULL",
                "CREATE INDEX IF NOT EXISTS ix_avaliacoes_experiencia_supervisor_usuario_id "
                "ON avaliacoes_experiencia (supervisor_usuario_id)",
            ),
        ),
    }

    for table_name, (column_name, statements) in migrations.items():
        if table_name in table_names:
            _run_column_migration(table_name, column_name, statements)

    # Os fluxos novos não possuem id do cadastro legado. As colunas antigas
    # permanecem preenchidas nas linhas antigas, mas deixam de ser obrigatórias.
    for table_name in ("rp_requisicoes", "rp_timeline", "controle_faltas"):
        if table_name not in table_names:
            continue
        try:
            with db.engine.begin() as connection:
                connection.execute(text(
                    f"ALTER TABLE {table_name} ALTER COLUMN supervisor_id DROP NOT NULL"
                ))
        except SQLAlchemyError:
            # Bancos instalados antes da constraint, ou dialetos sem a sintaxe,
            # continuam funcionais com o default do ORM.
            continue

    # Backfill único e idempotente: somente o cadastro legado que já possui
    # usuário associado pode virar vínculo oficial. Supervisores sem
    # ``usuario_id`` continuam deliberadamente sem uso nos fluxos atuais.
    backfill_tables = (
        "centro_de_custo",
        "rp_requisicoes",
        "rp_historico",
        "rp_timeline",
        "controle_faltas",
        "avaliacoes_experiencia",
    )
    if "supervisores" in table_names:
        available_tables = [
            table_name
            for table_name in backfill_tables
            if table_name in table_names
        ]
        if available_tables:
            try:
                with db.engine.begin() as connection:
                    for table_name in available_tables:
                        connection.execute(text(
                            f"UPDATE {table_name} AS target "
                            "SET supervisor_usuario_id = supervisor.usuario_id "
                            "FROM supervisores AS supervisor "
                            f"WHERE target.supervisor_usuario_id IS NULL "
                            "AND target.supervisor_id = supervisor.id "
                            "AND supervisor.usuario_id IS NOT NULL"
                        ))
            except SQLAlchemyError:
                # Um backfill incompleto é erro de schema e deve interromper o
                # startup para não expor avaliações com escopo incorreto.
                raise

    # As avaliações novas não precisam mais de um id do cadastro legado.
    if "avaliacoes_experiencia" in table_names:
        try:
            with db.engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE avaliacoes_experiencia "
                    "ALTER COLUMN supervisor_id DROP NOT NULL"
                ))
        except SQLAlchemyError:
            # Bancos que já tinham a coluna opcional ou não aceitam a sintaxe
            # continuam cobertos pela nulabilidade do modelo e do novo campo.
            pass


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
        _migrate_supervisor_users(table_names)
