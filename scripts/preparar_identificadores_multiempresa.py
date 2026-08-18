"""Prepara códigos empresariais sem romper as chaves legadas em uso.

Os ``id`` atuais permanecem como ponte para APIs e históricos existentes. Os
novos imports usam ``empresa_id + centro_id`` e ``empresa_id + matricula``;
assim códigos repetidos entre empresas nunca sobrescrevem a Costa Oeste.
"""

from __future__ import annotations

from os import getenv

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text


def _columns(engine, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table_name)}


def _unique_constraints(engine, table_name: str) -> list[str]:
    return [item["name"] for item in inspect(engine).get_unique_constraints(table_name) if item["name"]]


def _ensure_sequence(connection, table_name: str) -> None:
    sequence_name = f"{table_name}_id_multiempresa_seq"
    connection.execute(text(f"CREATE SEQUENCE IF NOT EXISTS {sequence_name}"))
    connection.execute(
        text(
            f"SELECT setval('{sequence_name}', "
            f"GREATEST(COALESCE((SELECT MAX(id) FROM {table_name}), 0), 1), TRUE)"
        )
    )
    connection.execute(
        text(
            f"ALTER TABLE {table_name} ALTER COLUMN id "
            f"SET DEFAULT nextval('{sequence_name}')"
        )
    )


def _foreign_key_names(engine, table_name: str, column_name: str) -> list[str]:
    return [
        foreign_key["name"]
        for foreign_key in inspect(engine).get_foreign_keys(table_name)
        if foreign_key.get("name") and column_name in foreign_key.get("constrained_columns", [])
    ]


def run() -> None:
    load_dotenv()
    database_uri = getenv("DB_URI")
    if not database_uri:
        raise RuntimeError("DB_URI não configurada.")

    engine = create_engine(
        database_uri,
        connect_args={"options": "-c lock_timeout=5s -c statement_timeout=120s"},
    )
    center_columns = _columns(engine, "centro_de_custo")
    employee_columns = _columns(engine, "colaboradores")
    employee_unique_constraints = _unique_constraints(engine, "colaboradores")
    rescission_columns = _columns(engine, "rh_rescisoes")
    rescission_registration_fks = _foreign_key_names(engine, "rh_rescisoes", "matricula")
    rescission_uid_fk_exists = "fk_rh_rescisoes_colaborador_uid" in {
        foreign_key["name"]
        for foreign_key in inspect(engine).get_foreign_keys("rh_rescisoes")
        if foreign_key.get("name")
    }

    with engine.begin() as connection:
        if "centro_id" not in center_columns:
            connection.execute(text("ALTER TABLE centro_de_custo ADD COLUMN centro_id INTEGER"))
            connection.execute(text("UPDATE centro_de_custo SET centro_id = id WHERE centro_id IS NULL"))
        if "nome" not in center_columns:
            connection.execute(text("ALTER TABLE centro_de_custo ADD COLUMN nome VARCHAR"))
            connection.execute(text("UPDATE centro_de_custo SET nome = local WHERE nome IS NULL"))
        _ensure_sequence(connection, "centro_de_custo")
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_centro_empresa_codigo "
                "ON centro_de_custo(empresa_id, centro_id)"
            )
        )

        if "uid" not in employee_columns:
            connection.execute(text("ALTER TABLE colaboradores ADD COLUMN uid BIGSERIAL"))
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_colaboradores_uid "
                    "ON colaboradores(uid)"
                )
            )
        _ensure_sequence(connection, "colaboradores")

        # Rescisões ainda depende da unicidade global da matrícula. Copiamos
        # a referência antes de removê-la, sem usar CASCADE ou apagar dados.
        if "colaborador_uid" not in rescission_columns:
            connection.execute(text("ALTER TABLE rh_rescisoes ADD COLUMN colaborador_uid BIGINT"))
        connection.execute(
            text(
                "UPDATE rh_rescisoes AS rescissao SET colaborador_uid = colaborador.uid "
                "FROM colaboradores AS colaborador "
                "WHERE rescissao.matricula = colaborador.matricula "
                "AND rescissao.colaborador_uid IS NULL"
            )
        )
        rescission_uid_fk = "fk_rh_rescisoes_colaborador_uid"
        if not rescission_uid_fk_exists:
            connection.execute(
                text(
                    "ALTER TABLE rh_rescisoes ADD CONSTRAINT "
                    "fk_rh_rescisoes_colaborador_uid "
                    "FOREIGN KEY (colaborador_uid) REFERENCES colaboradores(uid) "
                    "ON DELETE SET NULL NOT VALID"
                )
            )
        for foreign_key_name in rescission_registration_fks:
            connection.execute(
                text(f"ALTER TABLE rh_rescisoes DROP CONSTRAINT IF EXISTS {foreign_key_name}")
            )

        # Antes o identificador interno era forçado a ser a própria matrícula.
        # Após a separação por empresa isso não é verdade; o id vira ponte
        # interna estável e a matrícula é única apenas dentro da empresa.
        connection.execute(
            text(
                "ALTER TABLE colaboradores DROP CONSTRAINT IF EXISTS "
                "ck_colaboradores_id_matricula"
            )
        )

        # O modelo antigo tinha matrícula globalmente única. Isso é inválido
        # para a planilha consolidada, que possui milhares de códigos iguais
        # em empresas diferentes. Removemos apenas a unicidade isolada.
        for constraint_name in employee_unique_constraints:
            if constraint_name and "matricula" in constraint_name.lower():
                connection.execute(
                    text(f"ALTER TABLE colaboradores DROP CONSTRAINT IF EXISTS {constraint_name}")
                )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_colaborador_empresa_matricula "
                "ON colaboradores(empresa_id, matricula)"
            )
        )

    print("Identificadores multiempresa preparados.")


if __name__ == "__main__":
    run()
