"""Migração aditiva inicial para a separação por empresas.

Executar uma única vez antes de habilitar a importação multiempresa. Ela não
remove nem renomeia colunas legadas: o código atual do centro continua em
``centro_de_custo.id`` até que todos os consumidores tenham sido convertidos.
"""

from __future__ import annotations

from os import getenv

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

from models.empresas import Company
from utils.db import db


def _columns(engine, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table_name)}


def run() -> None:
    load_dotenv()
    database_uri = getenv("DB_URI")
    if not database_uri:
        raise RuntimeError("DB_URI não configurada.")

    engine = create_engine(
        database_uri,
        connect_args={"options": "-c lock_timeout=5s -c statement_timeout=90s"},
    )

    # A tabela é criada isoladamente para não depender da inicialização inteira
    # da API, que também sobe monitores e tarefas de websocket.
    Company.__table__.create(bind=engine, checkfirst=True)

    with engine.begin() as connection:
        costa_id = connection.execute(
            text(
                "SELECT id FROM empresas "
                "WHERE lower(nome) = 'costa oeste' LIMIT 1"
            )
        ).scalar()
        if costa_id is None:
            costa_id = connection.execute(
                text(
                    "INSERT INTO empresas (nome, ativa) VALUES "
                    "('COSTA OESTE', TRUE) RETURNING id"
                )
            ).scalar_one()

        center_columns = _columns(engine, "centro_de_custo")
        employee_columns = _columns(engine, "colaboradores")

        if "uid" not in center_columns:
            connection.execute(text("ALTER TABLE centro_de_custo ADD COLUMN uid BIGSERIAL"))
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "uq_centro_de_custo_uid ON centro_de_custo(uid)"
                )
            )
        if "empresa_id" not in center_columns:
            connection.execute(
                text(
                    "ALTER TABLE centro_de_custo ADD COLUMN empresa_id INTEGER "
                    "REFERENCES empresas(id) ON DELETE RESTRICT"
                )
            )
        if "empresa_id" not in employee_columns:
            connection.execute(
                text(
                    "ALTER TABLE colaboradores ADD COLUMN empresa_id INTEGER "
                    "REFERENCES empresas(id) ON DELETE RESTRICT"
                )
            )

        connection.execute(
            text(
                "UPDATE centro_de_custo SET empresa_id = :empresa_id "
                "WHERE empresa_id IS NULL"
            ),
            {"empresa_id": costa_id},
        )
        connection.execute(
            text(
                "UPDATE colaboradores SET empresa_id = :empresa_id "
                "WHERE empresa_id IS NULL"
            ),
            {"empresa_id": costa_id},
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_centro_empresa_codigo_legacy "
                "ON centro_de_custo(empresa_id, id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_colaboradores_empresa_matricula "
                "ON colaboradores(empresa_id, matricula)"
            )
        )

    with engine.connect() as connection:
        centers_without_company = connection.execute(
            text("SELECT count(*) FROM centro_de_custo WHERE empresa_id IS NULL")
        ).scalar_one()
        employees_without_company = connection.execute(
            text("SELECT count(*) FROM colaboradores WHERE empresa_id IS NULL")
        ).scalar_one()
        print("Migração fase 1 concluída.")
        print(f"Centros sem empresa: {centers_without_company}")
        print(f"Colaboradores sem empresa: {employees_without_company}")


if __name__ == "__main__":
    run()
