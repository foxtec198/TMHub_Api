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


def _migrate_dre_company(table_names):
    """Vincula as importações e lançamentos da DRE à empresa proprietária."""
    required_tables = {"dre_importacoes", "dre_lancamentos", "empresas"}
    if not required_tables.issubset(table_names):
        return

    # As colunas começam aceitando nulo para permitir o preenchimento seguro
    # de bases já existentes; ao final, a restrição torna a separação
    # multiempresa obrigatória para os próximos lançamentos.
    _run_column_migration(
        "dre_importacoes",
        "empresa_id",
        ("ALTER TABLE dre_importacoes ADD COLUMN empresa_id INTEGER",),
    )
    _run_column_migration(
        "dre_lancamentos",
        "empresa_id",
        ("ALTER TABLE dre_lancamentos ADD COLUMN empresa_id INTEGER",),
    )

    with db.engine.begin() as connection:
        connection.execute(text(
            "UPDATE dre_lancamentos AS lancamento "
            "SET empresa_id = centro.empresa_id "
            "FROM centro_de_custo AS centro "
            "WHERE centro.id = lancamento.centro_custo_id "
            "AND lancamento.empresa_id IS NULL"
        ))
        connection.execute(text(
            "UPDATE dre_importacoes AS importacao "
            "SET empresa_id = origem.empresa_id "
            "FROM ("
            "  SELECT importacao_id, MIN(empresa_id) AS empresa_id "
            "  FROM dre_lancamentos "
            "  WHERE empresa_id IS NOT NULL "
            "  GROUP BY importacao_id"
            ") AS origem "
            "WHERE origem.importacao_id = importacao.id "
            "AND importacao.empresa_id IS NULL"
        ))
        connection.execute(text(
            "UPDATE dre_importacoes AS importacao "
            "SET empresa_id = ("
            "  SELECT MIN(centro.empresa_id) "
            "  FROM filial_centros_custo AS vinculo "
            "  JOIN centro_de_custo AS centro ON centro.id = vinculo.centro_custo_id "
            "  WHERE vinculo.filial_id = importacao.filial_id"
            ") "
            "WHERE importacao.empresa_id IS NULL"
        ))

        missing_entries = connection.execute(text(
            "SELECT count(*) FROM dre_lancamentos WHERE empresa_id IS NULL"
        )).scalar_one()
        missing_imports = connection.execute(text(
            "SELECT count(*) FROM dre_importacoes WHERE empresa_id IS NULL"
        )).scalar_one()
        if missing_entries or missing_imports:
            raise RuntimeError(
                "A migração multiempresa da DRE encontrou registros sem empresa. "
                "Revise exclusivamente as tabelas dre_importacoes e dre_lancamentos."
            )

        connection.execute(text(
            "ALTER TABLE dre_importacoes ALTER COLUMN empresa_id SET NOT NULL"
        ))
        connection.execute(text(
            "ALTER TABLE dre_lancamentos ALTER COLUMN empresa_id SET NOT NULL"
        ))
        connection.execute(text(
            "DO $$ BEGIN "
            "IF NOT EXISTS (SELECT 1 FROM pg_constraint "
            "WHERE conname = 'fk_dre_importacoes_empresa') THEN "
            "ALTER TABLE dre_importacoes ADD CONSTRAINT fk_dre_importacoes_empresa "
            "FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT; "
            "END IF; "
            "IF NOT EXISTS (SELECT 1 FROM pg_constraint "
            "WHERE conname = 'fk_dre_lancamentos_empresa') THEN "
            "ALTER TABLE dre_lancamentos ADD CONSTRAINT fk_dre_lancamentos_empresa "
            "FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT; "
            "END IF; END $$;"
        ))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_dre_importacoes_empresa_competencia "
            "ON dre_importacoes (empresa_id, competencia)"
        ))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_dre_lancamentos_empresa_competencia_departamento "
            "ON dre_lancamentos (empresa_id, competencia, departamento)"
        ))


def _migrate_dre_manual_overrides(table_names):
    """Permite substituir valores importados sem remover sua fonte original."""
    if "dre_lancamentos" not in table_names:
        return

    _run_column_migration(
        "dre_lancamentos",
        "substitui_importacao",
        (
            "ALTER TABLE dre_lancamentos "
            "ADD COLUMN substitui_importacao BOOLEAN NOT NULL DEFAULT FALSE",
        ),
    )


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
        _migrate_dre_company(table_names)
        _migrate_dre_manual_overrides(table_names)
