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

from import_col.date_normalization import normalize_import_date

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
    parsed = normalize_import_date(value, field="data de admissão")
    if parsed is None:
        raise ValueError("data de admissão ausente")
    return parsed


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
            admission_value = item.get("admissao")
            if admission_value in (None, ""):
                admission_value = item.get("data_admissao")
            admission = parse_admission(admission_value)
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


def validate_cost_center_identities(employees):
    """Valida a chave operacional de centros usada pela importação diária.

    A identidade de resolução é ``empresa + centro_id``. Ela permite, por
    exemplo, que 44000 da Facilities seja Scherer e 44000 da Costa Oeste seja
    Copel, sem qualquer colisão. O nome do centro é catálogo: não é requisito
    da carga diária e não pode alterar o cadastro já aprovado.
    """
    invalid = []
    for item in employees:
        company = item.get("_empresa_id") or normalize_name(item.get("empresa_nome"))
        center_code = item.get("centro_custo_num")
        if company is None or center_code in (None, ""):
            invalid.append(item)
            continue
        try:
            int(center_code)
        except (TypeError, ValueError):
            invalid.append(item)
    if invalid:
        raise ValueError(
            "Existem colaboradores sem empresa ou centro de custo numérico. "
            "Corrija o relatório antes de importar."
        )


def create_cost_centers(connection, employees, *, sync_catalog=False):
    """Resolve centros por empresa + código para a importação.

    No modo normal a importação diária **não cria nem altera** centros. No
    modo ``sync_catalog`` (planilha completa, confirmado pelo administrador),
    os nomes/localizações informados atualizam o catálogo corporativo antes do
    vínculo dos colaboradores. Isso impede que relatórios cotidianos mudem
    nomes de contratos por acidente.
    """
    validate_cost_center_identities(employees)
    requested_centers = {}
    catalog_entries = {}
    for item in employees:
        key = (item["_empresa_id"], int(item["centro_custo_num"]))
        requested_centers.setdefault(key[0], set()).add(key[1])
        center_name = " ".join(str(item.get("centro_custo") or "").split())
        # Um código isolado (ex.: "44000") não é um nome de catálogo e não
        # pode substituir um contrato já cadastrado caso a opção seja marcada
        # por engano. O catálogo exige uma descrição de fato.
        if sync_catalog and center_name and not fullmatch(r"\d+", center_name):
            catalog_entries[key] = {
                "empresa_id": key[0],
                "centro_id": key[1],
                "local": center_name,
                "nome": center_name,
                "departamento": item.get("departamento_codigo"),
                "cidade_id": item.get("cidade_id") or None,
            }

    resolved_centers = {}
    for company_id, center_codes in requested_centers.items():
        rows = connection.execute(
            text("""
                SELECT id, empresa_id, centro_id, nome, local, departamento, cidade_id
                FROM centro_de_custo
                WHERE empresa_id = :empresa_id AND centro_id = ANY(:center_codes)
            """),
            {"empresa_id": company_id, "center_codes": sorted(center_codes)},
        ).mappings()
        for row in rows:
            resolved_centers[(row["empresa_id"], row["centro_id"])] = dict(row)

    created = updated = 0
    if sync_catalog:
        for key, center in tqdm(catalog_entries.items(), desc="Sincronizando catálogo de centros"):
            existing = resolved_centers.get(key)
            if existing is None:
                inserted = connection.execute(
                    text("""
                        INSERT INTO centro_de_custo
                            (empresa_id, centro_id, local, nome, departamento, cidade_id)
                        VALUES (:empresa_id, :centro_id, :local, :nome, :departamento, :cidade_id)
                        RETURNING id, empresa_id, centro_id, nome, local
                    """),
                    center,
                ).mappings().one()
                resolved_centers[key] = dict(inserted)
                created += 1
                continue

            changed = {
                field: value
                for field, value in center.items()
                if field in {"nome", "local", "departamento", "cidade_id"}
                and value is not None
                and value != existing.get(field)
            }
            if changed:
                connection.execute(
                    text("""
                        UPDATE centro_de_custo
                        SET nome = :nome,
                            local = :local,
                            departamento = :departamento,
                            cidade_id = :cidade_id
                        WHERE id = :id
                    """),
                    {
                        "nome": changed.get("nome", existing["nome"]),
                        "local": changed.get("local", existing["local"]),
                        "departamento": changed.get("departamento", existing["departamento"]),
                        "cidade_id": changed.get("cidade_id", existing["cidade_id"]),
                        "id": existing["id"],
                    },
                )
                updated += 1

    missing_centers = [
        key for company_id, center_codes in requested_centers.items()
        for key in ((company_id, center_code) for center_code in center_codes)
        if key not in resolved_centers
    ]
    if missing_centers:
        preview = ", ".join(
            f"empresa {company_id}, centro {center_id}"
            for company_id, center_id in missing_centers[:8]
        )
        raise ValueError(
            "Centro(s) não encontrado(s) no catálogo corporativo: "
            f"{preview}. Use uma planilha completa e marque 'Sincronizar catálogo de centros' "
            "antes da importação diária."
        )

    for item in employees:
        key = (item["_empresa_id"], int(item["centro_custo_num"]))
        center = resolved_centers[key]
        item["_centro_db_id"] = center["id"]
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
            "SELECT id, empresa_id, matricula, nome, centro_id, "
            "data_admissao, situacao, cargo, carga_horaria, salario, cpf "
            "FROM colaboradores WHERE empresa_id = ANY(:company_ids)"
        ),
        {"company_ids": company_ids},
    ).mappings()
    existing = {(row["empresa_id"], row["matricula"]): dict(row) for row in existing_rows}
    insert_rows = []
    updates_by_fields = {}
    ignored = 0

    def comparable(field, value):
        if isinstance(value, Decimal):
            return value.normalize()
        if field == "data_admissao":
            return normalize_import_date(value, field="data de admissão")
        return value

    for processed, item in enumerate(tqdm(employees, desc="Sincronizando colaboradores"), start=1):
        name = sub(r"[\d'\".,]", "", str(item.get("nome") or "")).strip()
        values = {
            "matricula": item["_matricula"],
            "empresa_id": item["_empresa_id"],
            "nome": name,
            "centro_id": item.get("_centro_db_id"),
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
            current_admission = normalize_import_date(
                current.get("data_admissao"),
                field="data de admissão",
            )
            if current_admission and values["data_admissao"] < current_admission:
                ignored += 1
            else:
                changed_fields = tuple(
                    field
                    for field in (
                        "nome", "centro_id", "data_admissao",
                        "situacao", "cargo", "carga_horaria", "salario", "cpf",
                    )
                    if comparable(field, current.get(field)) != comparable(field, values.get(field))
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
                "(matricula, empresa_id, nome, centro_id, data_admissao, "
                "situacao, cargo, carga_horaria, salario, cpf) "
                "VALUES (:matricula, :empresa_id, :nome, :centro_id, "
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
