"""Copia referências legadas de centro para a identidade estável ``uid``.

Esta é uma fase compatível: as colunas originais continuam intactas e o
relatório final aponta registros sem correspondência antes de qualquer corte
definitivo para a chave interna multiempresa.
"""

from __future__ import annotations

from os import getenv

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text


# tabela, coluna legada, nova coluna, comportamento da FK em exclusões
REFERENCE_MAPPINGS = (
    ("colaboradores", "centro_id", "centro_uid", "SET NULL"),
    ("ad_entrevistas_historico", "centro_custo_id", "centro_custo_uid", "SET NULL"),
    ("ad_vagas", "centro_custo_id", "centro_custo_uid", "RESTRICT"),
    ("controle_faltas", "centro_custo_id", "centro_custo_uid", "RESTRICT"),
    ("controle_glosas", "centro_custo_id", "centro_custo_uid", "RESTRICT"),
    ("es_movimento_destinatarios", "centro_custo_id", "centro_custo_uid", "RESTRICT"),
    ("estrutura_ativos", "centro_custo_id", "centro_custo_uid", "RESTRICT"),
    ("estrutura_locais", "centro_custo_id", "centro_custo_uid", "RESTRICT"),
    ("estrutura_ativo_movimentacoes", "centro_custo_origem_id", "centro_custo_origem_uid", "SET NULL"),
    ("estrutura_ativo_movimentacoes", "centro_custo_destino_id", "centro_custo_destino_uid", "SET NULL"),
    ("filial_centros_custo", "centro_custo_id", "centro_custo_uid", "RESTRICT"),
    ("schedular_rotinas", "centro_custo_id", "centro_custo_uid", "CASCADE"),
    ("schedular_tarefas", "centro_custo_id", "centro_custo_uid", "SET NULL"),
    ("rp_requisicoes", "cc", "centro_uid", "SET NULL"),
    ("rp_historico", "cc", "centro_uid", "SET NULL"),
    ("rp_timeline", "cc", "centro_uid", "SET NULL"),
)


def _table_columns(engine, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table_name)}


def _constraint_name(table_name: str, target_column: str) -> str:
    return f"fk_{table_name}_{target_column}_centro_uid"[:60]


def run() -> None:
    load_dotenv()
    database_uri = getenv("DB_URI")
    if not database_uri:
        raise RuntimeError("DB_URI não configurada.")

    engine = create_engine(
        database_uri,
        connect_args={"options": "-c lock_timeout=5s -c statement_timeout=120s"},
    )
    available_tables = set(inspect(engine).get_table_names())
    # A reflexão precisa ocorrer antes do primeiro ALTER. Caso contrário, uma
    # segunda conexão do inspector fica bloqueada pelo próprio lock exclusivo
    # desta transação PostgreSQL.
    columns_by_table = {
        table_name: _table_columns(engine, table_name)
        for table_name, _, _, _ in REFERENCE_MAPPINGS
        if table_name in available_tables
    }
    report: list[tuple[str, str, int]] = []

    with engine.begin() as connection:
        for table_name, legacy_column, uid_column, on_delete in REFERENCE_MAPPINGS:
            if table_name not in available_tables:
                continue

            columns = columns_by_table[table_name]
            if legacy_column not in columns:
                continue
            if uid_column not in columns:
                connection.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN {uid_column} BIGINT")
                )

            connection.execute(
                text(
                    f"UPDATE {table_name} AS target "
                    "SET " + uid_column + " = center_ref.uid "
                    "FROM centro_de_custo AS center_ref "
                    "WHERE target." + legacy_column + " = center_ref.id "
                    "AND target." + uid_column + " IS NULL"
                )
            )
            connection.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS ix_{table_name}_{uid_column} "
                    f"ON {table_name}({uid_column})"
                )
            )
            constraint_name = _constraint_name(table_name, uid_column)
            constraint_exists = connection.execute(
                text("SELECT 1 FROM pg_constraint WHERE conname = :constraint_name"),
                {"constraint_name": constraint_name},
            ).scalar()
            if not constraint_exists:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} "
                        f"FOREIGN KEY ({uid_column}) REFERENCES centro_de_custo(uid) "
                        f"ON DELETE {on_delete} NOT VALID"
                    )
                )
            unmatched = connection.execute(
                text(
                    f"SELECT count(*) FROM {table_name} AS target "
                    f"WHERE target.{legacy_column} IS NOT NULL "
                    f"AND target.{uid_column} IS NULL"
                )
            ).scalar_one()
            report.append((table_name, uid_column, unmatched))

    print("Referências copiadas para centro uid.")
    for table_name, uid_column, unmatched in report:
        print(f"{table_name}.{uid_column}: sem correspondência = {unmatched}")


if __name__ == "__main__":
    run()
