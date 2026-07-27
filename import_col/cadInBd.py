r"""Sincroniza centros de custo e colaboradores vindos do arquivo ``cols``.

A matricula e a chave primaria de colaboradores. Quando uma matricula aparece
mais de uma vez, sempre prevalece o vinculo com a admissao mais recente.

Uso:
    venv\Scripts\python.exe import_col\cadInBd.py
    venv\Scripts\python.exe import_col\cadInBd.py --centros
"""

from argparse import ArgumentParser
from datetime import date, datetime
from os import getenv
from re import fullmatch, sub

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from tqdm import tqdm

from cols import cols


load_dotenv()


def normalize_registration(value):
    """Converte uma matricula inteira, tolerando apenas espacos/quebras."""
    if isinstance(value, bool) or value is None:
        raise ValueError("matricula ausente")
    if isinstance(value, int):
        registration = value
    elif isinstance(value, float) and value.is_integer():
        registration = int(value)
    else:
        normalized = sub(r"\s+", "", str(value))
        if not fullmatch(r"\d+", normalized):
            raise ValueError(f"matricula invalida: {value!r}")
        registration = int(normalized)
    if registration <= 0 or registration > 2_147_483_647:
        raise ValueError(f"matricula fora do intervalo: {value!r}")
    return registration


def parse_admission(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    raw = str(value or "").strip()
    for pattern in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, pattern)
        except ValueError:
            continue
    raise ValueError(f"data de admissao invalida: {value!r}")


def parse_decimal(value, default=0.0):
    if value in (None, ""):
        return default
    if isinstance(value, str):
        value = value.replace(".", "").replace(",", ".")
    return float(value)


def latest_employees(items):
    """Deduplica a carga e conserva a admissao mais recente por matricula."""
    selected = {}
    invalid = []
    duplicates = 0
    for item in items:
        try:
            registration = normalize_registration(item.get("codigo"))
            admission = parse_admission(item.get("admissao"))
        except (TypeError, ValueError) as exc:
            invalid.append(str(exc))
            continue

        prepared = dict(item)
        prepared["_matricula"] = registration
        prepared["_admissao"] = admission
        current = selected.get(registration)
        if current is not None:
            duplicates += 1
        if current is None or admission >= current["_admissao"]:
            selected[registration] = prepared
    return list(selected.values()), invalid, duplicates


def create_cost_centers(connection, employees):
    centers = {}
    for item in employees:
        center_id = item.get("centro_custo_num")
        if center_id is None:
            continue
        centers[center_id] = {
            "id": center_id,
            "local": item.get("centro_custo"),
            "dpto": item.get("departamento_codigo") or 0,
            "cidade_id": item.get("cidade_id") or 0,
        }

    created = updated = 0
    statement = text("""
        INSERT INTO centro_de_custo (id, local, departamento, cidade_id)
        VALUES (:id, :local, :dpto, :cidade_id)
        ON CONFLICT (id) DO UPDATE
        SET local = EXCLUDED.local,
            departamento = EXCLUDED.departamento,
            cidade_id = EXCLUDED.cidade_id
        RETURNING (xmax = 0) AS inserted
    """)
    for center in tqdm(centers.values(), desc="Sincronizando centros de custo"):
        inserted = connection.execute(statement, center).scalar_one()
        created += int(inserted)
        updated += int(not inserted)
    return created, updated


def create_employees(connection, employees):
    positions = {
        row.nome: row.id
        for row in connection.execute(text("SELECT nome, id FROM cargos"))
    }
    statement = text("""
        INSERT INTO colaboradores (
            id, matricula, nome, centro_id, data_admissao,
            situacao, cargo, carga_horaria, salario, cpf
        )
        VALUES (
            :matricula, :matricula, :nome, :centro_id, :admissao,
            :situacao, :cargo_id, :carga_horaria, :salario, :cpf
        )
        ON CONFLICT (id) DO UPDATE
        SET matricula = EXCLUDED.matricula,
            nome = EXCLUDED.nome,
            centro_id = EXCLUDED.centro_id,
            data_admissao = EXCLUDED.data_admissao,
            situacao = EXCLUDED.situacao,
            cargo = EXCLUDED.cargo,
            carga_horaria = EXCLUDED.carga_horaria,
            salario = EXCLUDED.salario,
            cpf = EXCLUDED.cpf
        WHERE colaboradores.data_admissao IS NULL
           OR EXCLUDED.data_admissao >= colaboradores.data_admissao
        RETURNING (xmax = 0) AS inserted
    """)

    created = updated = ignored = 0
    for item in tqdm(employees, desc="Sincronizando colaboradores"):
        name = sub(r"[\d'\".,]", "", str(item.get("nome") or "")).strip()
        result = connection.execute(
            statement,
            {
                "matricula": item["_matricula"],
                "nome": name,
                "centro_id": item.get("centro_custo_num"),
                "admissao": item["_admissao"],
                "situacao": item.get("situacao"),
                "cargo_id": positions.get(item.get("cargo"), 0),
                "carga_horaria": parse_decimal(item.get("hor")),
                "salario": parse_decimal(item.get("salario")),
                "cpf": item.get("cpf"),
            },
        ).first()
        if result is None:
            ignored += 1
        elif result[0]:
            created += 1
        else:
            updated += 1
    return created, updated, ignored


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "--centros",
        action="store_true",
        help="Sincroniza os centros de custo antes dos colaboradores.",
    )
    args = parser.parse_args()

    database_uri = getenv("DB_URI")
    if not database_uri:
        raise RuntimeError("DB_URI nao configurada")

    employees, invalid, duplicates = latest_employees(cols["empregados"])
    print(
        f"Carga: {len(employees)} matriculas validas, "
        f"{duplicates} duplicidades e {len(invalid)} registros invalidos."
    )
    if invalid:
        for error in invalid[:10]:
            print(f"- Ignorado: {error}")

    engine = create_engine(database_uri)
    with engine.begin() as connection:
        if args.centros:
            created, updated = create_cost_centers(connection, employees)
            print(f"Centros de custo: {created} criados, {updated} atualizados.")

        created, updated, ignored = create_employees(connection, employees)
        print(
            f"Colaboradores: {created} criados, {updated} atualizados e "
            f"{ignored} ignorados por possuirem admissao mais recente no banco."
        )


if __name__ == "__main__":
    main()
