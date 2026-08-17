# Rotinas de importação de colaboradores: persistência da importação.
r"""Sincroniza centros de custo e colaboradores vindos do arquivo ``cols``.

A matricula e a chave primaria de colaboradores. Quando uma matricula aparece
mais de uma vez, sempre prevalece o vinculo com a admissao mais recente.

Uso:
    venv\Scripts\python.exe import_col\cadInBd.py
    venv\Scripts\python.exe import_col\cadInBd.py --centros
"""

# Biblioteca padrão.
from argparse import ArgumentParser
from datetime import date, datetime
from os import getenv
from re import fullmatch, sub
from unicodedata import combining, normalize

# Dependências externas.
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from tqdm import tqdm

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


def normalize_name(value):
    text_value = normalize("NFKD", str(value or "").upper())
    text_value = "".join(char for char in text_value if not combining(char))
    return sub(r"[^A-Z0-9]+", " ", text_value).strip()


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
            "cidade_id": item.get("cidade_id") or None,
        }

    created = updated = 0
    statement = text("""
        INSERT INTO centro_de_custo (id, local, departamento, cidade_id)
        VALUES (:id, :local, :dpto, :cidade_id)
        ON CONFLICT (id) DO UPDATE
        SET local = CASE
                WHEN trim(coalesce(EXCLUDED.local, '')) ~ '^[0-9]+$'
                    AND trim(coalesce(centro_de_custo.local, '')) <> ''
                    THEN centro_de_custo.local
                ELSE EXCLUDED.local
            END,
            departamento = EXCLUDED.departamento,
            cidade_id = EXCLUDED.cidade_id
        RETURNING (xmax = 0) AS inserted
    """)
    for center in tqdm(centers.values(), desc="Sincronizando centros de custo"):
        inserted = connection.execute(statement, center).scalar_one()
        created += int(inserted)
        updated += int(not inserted)
    return created, updated


def ensure_positions(connection, employees):
    positions = {
        normalize_name(row["nome"]): row["id"]
        for row in connection.execute(text("SELECT nome, id FROM cargos")).mappings()
        if normalize_name(row["nome"])
    }
    created = 0
    for item in employees:
        cargo_name = str(item.get("cargo") or "").strip().upper()
        cargo_key = normalize_name(cargo_name)
        if not cargo_key or cargo_key in positions:
            continue
        cargo_id = connection.execute(
            text(
                "INSERT INTO cargos (nome, multa, active) "
                "VALUES (:nome, NULL, TRUE) RETURNING id"
            ),
            {"nome": cargo_name},
        ).scalar_one()
        positions[cargo_key] = cargo_id
        created += 1
    return positions, created


def create_employees(connection, employees, positions=None, progress_callback=None):
    if positions is None:
        positions, _ = ensure_positions(connection, employees)
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
    for processed, item in enumerate(tqdm(employees, desc="Sincronizando colaboradores"), start=1):
        name = sub(r"[\d'\".,]", "", str(item.get("nome") or "")).strip()
        result = connection.execute(
            statement,
            {
                "matricula": item["_matricula"],
                "nome": name,
                "centro_id": item.get("centro_custo_num"),
                "admissao": item["_admissao"],
                "situacao": item.get("situacao"),
                "cargo_id": positions.get(normalize_name(item.get("cargo"))),
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
        if progress_callback:
            progress_callback(processed)
    return created, updated, ignored


def link_supervisors_to_employees(connection, employees):
    """Vincula o cadastro operacional do supervisor à sua matrícula."""
    supervisors = connection.execute(
        text("SELECT id, nome, colaborador_id FROM supervisores ORDER BY id")
    ).mappings().all()
    positions = {
        row.id: row.nome
        for row in connection.execute(text("SELECT id, nome FROM cargos"))
    }
    candidates_by_name = {}
    for item in employees:
        name_key = normalize_name(item.get("nome"))
        candidates_by_name.setdefault(name_key, []).append(item)

    linked = unresolved = 0
    statement = text(
        "UPDATE supervisores SET colaborador_id = :employee_id WHERE id = :supervisor_id"
    )
    for supervisor in supervisors:
        candidates = candidates_by_name.get(normalize_name(supervisor["nome"]), [])
        candidates.sort(
            key=lambda item: (
                int(str(item.get("situacao")) == "1"),
                int("SUPERVISOR" in str(positions.get(item.get("cargo_id"), item.get("cargo")) or "").upper()),
                item["_admissao"],
            ),
            reverse=True,
        )
        if not candidates:
            unresolved += 1
            continue
        connection.execute(
            statement,
            {
                "employee_id": candidates[0]["_matricula"],
                "supervisor_id": supervisor["id"],
            },
        )
        linked += 1
    return linked, unresolved


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

    try:
        from import_col.cols import _load_cols
    except ModuleNotFoundError:
        from cols import _load_cols

    employees, invalid, duplicates = latest_employees(_load_cols()["empregados"])
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

        positions, created_positions = ensure_positions(connection, employees)
        print(f"Cargos: {created_positions} criados.")
        created, updated, ignored = create_employees(connection, employees, positions)
        print(
            f"Colaboradores: {created} criados, {updated} atualizados e "
            f"{ignored} ignorados por possuirem admissao mais recente no banco."
        )
        linked, unresolved = link_supervisors_to_employees(connection, employees)
        print(
            f"Supervisores: {linked} vinculados às matrículas e "
            f"{unresolved} sem correspondência."
        )


if __name__ == "__main__":
    main()
