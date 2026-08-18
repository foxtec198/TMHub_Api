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
from decimal import Decimal
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
    """Deduplica por empresa + matrícula e mantém a admissão mais recente."""
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
        company_key = normalize_name(item.get("empresa_nome") or "COSTA OESTE")
        key = (company_key, registration)
        current = selected.get(key)
        if current is not None:
            duplicates += 1
        if current is None or admission >= current["_admissao"]:
            selected[key] = prepared
    return list(selected.values()), invalid, duplicates


def ensure_companies(connection, employees):
    """Obtém ou cria empresas antes de vincular centros e colaboradores."""
    companies = {
        normalize_name(row["nome"]): row["id"]
        for row in connection.execute(text("SELECT id, nome FROM empresas")).mappings()
    }
    created = 0
    for item in employees:
        name = str(item.get("empresa_nome") or "COSTA OESTE").strip().upper()
        key = normalize_name(name)
        if not key or key in companies:
            continue
        company_id = connection.execute(
            text("INSERT INTO empresas (nome, ativa) VALUES (:nome, TRUE) RETURNING id"),
            {"nome": name},
        ).scalar_one()
        companies[key] = company_id
        created += 1
    for item in employees:
        item["_empresa_id"] = companies[normalize_name(item.get("empresa_nome") or "COSTA OESTE")]
    return companies, created


def create_cost_centers(connection, employees):
    centers = {}
    for item in employees:
        center_id = item.get("centro_custo_num")
        if center_id is None:
            continue
        key = (item["_empresa_id"], center_id)
        centers[key] = {
            "empresa_id": item["_empresa_id"],
            "centro_id": center_id,
            "local": item.get("centro_custo"),
            "nome": item.get("centro_custo"),
            "dpto": item.get("departamento_codigo") or 0,
            "cidade_id": item.get("cidade_id") or None,
        }

    created = updated = 0
    statement = text("""
        INSERT INTO centro_de_custo
            (empresa_id, centro_id, local, nome, departamento, cidade_id)
        VALUES (:empresa_id, :centro_id, :local, :nome, :dpto, :cidade_id)
        ON CONFLICT (empresa_id, centro_id) DO UPDATE
        SET local = CASE
                WHEN trim(coalesce(EXCLUDED.local, '')) ~ '^[0-9]+$'
                    AND trim(coalesce(centro_de_custo.local, '')) <> ''
                    THEN centro_de_custo.local
                WHEN EXCLUDED.local IS NULL
                    THEN centro_de_custo.local
                ELSE EXCLUDED.local
            END,
            nome = COALESCE(EXCLUDED.nome, centro_de_custo.nome),
            departamento = EXCLUDED.departamento,
            cidade_id = EXCLUDED.cidade_id
        RETURNING id, uid, (xmax = 0) AS inserted
    """)
    resolved_centers = {}
    for center in tqdm(centers.values(), desc="Sincronizando centros de custo"):
        result = connection.execute(statement, center).mappings().one()
        resolved_centers[(center["empresa_id"], center["centro_id"])] = result
        created += int(result["inserted"])
        updated += int(not result["inserted"])
    for item in employees:
        center = resolved_centers.get((item["_empresa_id"], item.get("centro_custo_num")))
        if center:
            item["_centro_db_id"] = center["id"]
            item["_centro_uid"] = center["uid"]
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
    company_ids = sorted({item["_empresa_id"] for item in employees})
    existing_rows = connection.execute(
        text(
            "SELECT id, empresa_id, matricula, nome, centro_id, centro_uid, "
            "data_admissao, situacao, cargo, carga_horaria, salario, cpf "
            "FROM colaboradores WHERE empresa_id = ANY(:company_ids)"
        ),
        {"company_ids": company_ids},
    ).mappings()
    existing = {(row["empresa_id"], row["matricula"]): dict(row) for row in existing_rows}
    insert_rows = []
    updates_by_fields = {}
    ignored = 0

    def comparable(value):
        if isinstance(value, Decimal):
            return value.normalize()
        if isinstance(value, datetime):
            return value.replace(tzinfo=None)
        return value

    for processed, item in enumerate(tqdm(employees, desc="Sincronizando colaboradores"), start=1):
        name = sub(r"[\d'\".,]", "", str(item.get("nome") or "")).strip()
        values = {
            "matricula": item["_matricula"],
            "empresa_id": item["_empresa_id"],
            "nome": name,
            "centro_id": item.get("_centro_db_id"),
            "centro_uid": item.get("_centro_uid"),
            "data_admissao": item["_admissao"],
            "situacao": item.get("situacao"),
            "cargo": positions.get(normalize_name(item.get("cargo"))),
            "carga_horaria": parse_decimal(item.get("hor")),
            "salario": parse_decimal(item.get("salario")),
            "cpf": item.get("cpf"),
        }
        current = existing.get((values["empresa_id"], values["matricula"]))
        if current is None:
            insert_rows.append(values)
        else:
            # Nunca substitui a fotografia de uma admissão mais recente por
            # um relatório anterior, mas permite atualizar campos de mesma
            # admissão somente quando houver divergência real.
            if current["data_admissao"] and values["data_admissao"] < current["data_admissao"]:
                ignored += 1
            else:
                changed_fields = tuple(
                    field
                    for field in (
                        "nome", "centro_id", "centro_uid", "data_admissao",
                        "situacao", "cargo", "carga_horaria", "salario", "cpf",
                    )
                    if comparable(current.get(field)) != comparable(values.get(field))
                )
                if changed_fields:
                    updates_by_fields.setdefault(changed_fields, []).append(
                        {"id": current["id"], **{field: values[field] for field in changed_fields}}
                    )
                else:
                    ignored += 1
        if progress_callback:
            progress_callback(processed)

    if insert_rows:
        connection.execute(
            text(
                "INSERT INTO colaboradores "
                "(matricula, empresa_id, nome, centro_id, centro_uid, data_admissao, "
                "situacao, cargo, carga_horaria, salario, cpf) "
                "VALUES (:matricula, :empresa_id, :nome, :centro_id, :centro_uid, "
                ":data_admissao, :situacao, :cargo, :carga_horaria, :salario, :cpf)"
            ),
            insert_rows,
        )
    updated = 0
    for fields, rows in updates_by_fields.items():
        assignments = ", ".join(f"{field} = :{field}" for field in fields)
        connection.execute(text(f"UPDATE colaboradores SET {assignments} WHERE id = :id"), rows)
        updated += len(rows)
    return len(insert_rows), updated, ignored


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
        if normalize_name(item.get("empresa_nome") or "COSTA OESTE") != "COSTA OESTE":
            continue
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
        _, created_companies = ensure_companies(connection, employees)
        print(f"Empresas: {created_companies} criadas.")
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
