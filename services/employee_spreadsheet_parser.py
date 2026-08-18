"""Leitor normalizado dos relatórios XLS/XLSX de colaboradores.

O relatório corporativo pode reunir mais de uma empresa na mesma aba. A
empresa é identificada pelo cabeçalho do arquivo e, nos blocos seguintes, pelo
prefixo do departamento (por exemplo ``FACILITIES - ADMINISTRATIVO``).
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from re import match, sub
from typing import Any, Iterable
from unicodedata import combining, normalize


SUPPORTED_EXTENSIONS = {".xls", ".xlsx"}
COMPANY_TOKENS = ("COSTA OESTE", "FACILITIES", "GRABIN", "MAG")
HEADER_COLUMNS = {
    "codigo": 0,
    "nome": 4,
    "cargo": 11,
    "centro_custo_num": 18,
    "hor": 20,
    "admissao": 22,
    "situacao": 26,
    "cpf": 28,
    "salario": 32,
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _normalized(value: Any) -> str:
    decomposed = normalize("NFKD", _clean(value).upper())
    return "".join(char for char in decomposed if not combining(char))


def _known_company(value: Any) -> str | None:
    normalized = _normalized(value)
    for token in COMPANY_TOKENS:
        # Cabeçalho corporativo ("COSTA OESTE SERVIÇOS") ou o prefixo do
        # departamento ("1 - FACILITIES - ..."). Não basta procurar o texto
        # em qualquer ponto: um contrato pode citar "MAG" no próprio nome.
        if normalized.startswith(token) or match(rf"^\d+\s*-\s*{token}(?:\s|-|$)", normalized):
            return token
    return None


def _company_name(value: Any, fallback: str) -> str:
    known_company = _known_company(value)
    if known_company:
        return known_company
    cleaned = _clean(value)
    return cleaned or fallback


def _filename_company(filename: str) -> str:
    name = Path(filename).stem.replace("_", " ")
    return _company_name(name, "COSTA OESTE")


def _department_details(row: tuple[Any, ...]) -> tuple[str, int | None] | None:
    joined = " ".join(_clean(value) for value in row if _clean(value))
    if "DEPARTAMENTO:" not in _normalized(joined):
        return None
    # O layout padrão possui a descrição depois do rótulo. Mantemos também
    # uma busca no texto completo para formatos exportados com colunas unidas.
    values = [_clean(value) for value in row if _clean(value)]
    description = next(
        (value for value in values if " - " in value and "DEPARTAMENTO" not in _normalized(value)),
        joined,
    )
    number_match = match(r"\s*(\d+)", description)
    code = int(number_match.group(1)) if number_match else None
    return description, code


def _as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        digits = sub(r"\D", "", str(value))
        return int(digits) if digits else None


def _cell(row: tuple[Any, ...], key: str) -> Any:
    index = HEADER_COLUMNS[key]
    return row[index] if len(row) > index else None


def _is_employee_row(row: tuple[Any, ...]) -> bool:
    return _as_int(_cell(row, "codigo")) is not None and bool(_clean(_cell(row, "nome")))


def _xlsx_rows(path: Path) -> Iterable[tuple[Any, ...]]:
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        for sheet in workbook.worksheets:
            yield from sheet.iter_rows(values_only=True)
    finally:
        workbook.close()


def _xls_rows(path: Path) -> Iterable[tuple[Any, ...]]:
    try:
        import xlrd
    except ModuleNotFoundError as error:
        raise ValueError(
            "Leitura de .xls indisponível. Instale a dependência xlrd no servidor."
        ) from error

    workbook = xlrd.open_workbook(path)
    for sheet in workbook.sheets():
        for row_index in range(sheet.nrows):
            yield tuple(sheet.row_values(row_index))


def _rows(path: Path) -> Iterable[tuple[Any, ...]]:
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        return _xlsx_rows(path)
    if suffix == ".xls":
        return _xls_rows(path)
    raise ValueError("Formato não suportado. Envie .xls ou .xlsx.")


def parse_employee_spreadsheet(
    path: str | Path,
    filename: str | None = None,
    centro_forcado: int | None = None,
) -> dict[str, Any]:
    """Converte uma planilha de relatório em registros de importação.

    Retorna colaboradores já identificados por empresa e uma lista de avisos;
    não persiste dados nem cria empresas nesta camada.
    """

    source_path = Path(path)
    if source_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Formato não suportado. Envie .xls ou .xlsx.")

    fallback_company = _filename_company(filename or source_path.name)
    if centro_forcado is not None and int(centro_forcado) <= 0:
        raise ValueError("O centro forçado deve ser um código positivo.")
    forced_center = int(centro_forcado) if centro_forcado is not None else None
    current_company = fallback_company
    current_department = ""
    current_department_code: int | None = None
    employees: list[dict[str, Any]] = []
    invalid: list[str] = []
    companies: set[str] = set()

    for row_number, raw_row in enumerate(_rows(source_path), start=1):
        row = tuple(raw_row)
        first_cell = _clean(row[0] if row else None)
        if first_cell and "SERVICOS" in _normalized(first_cell):
            current_company = _company_name(first_cell, fallback_company)

        department = _department_details(row)
        if department:
            current_department, current_department_code = department
            current_company = _known_company(current_department) or current_company
            continue
        if not _is_employee_row(row):
            continue

        registration = _as_int(_cell(row, "codigo"))
        center_code = forced_center or _as_int(_cell(row, "centro_custo_num"))
        admission = _cell(row, "admissao")
        if not registration or not center_code or not isinstance(admission, (date, datetime)):
            invalid.append(f"Linha {row_number}: matrícula, centro ou admissão inválidos.")
            continue

        company = _company_name(current_company, fallback_company)
        companies.add(company)
        employees.append(
            {
                "codigo": registration,
                "nome": _clean(_cell(row, "nome")),
                "cargo": _clean(_cell(row, "cargo")),
                "centro_custo_num": center_code,
                # O relatório não entrega o nome do centro. O importador só
                # atualiza "local" quando vier uma descrição verdadeira.
                "centro_custo": None,
                "hor": _cell(row, "hor"),
                "admissao": admission,
                "situacao": _as_int(_cell(row, "situacao")),
                "cpf": _clean(_cell(row, "cpf")) or None,
                "salario": _cell(row, "salario"),
                "departamento": current_department,
                "departamento_codigo": current_department_code,
                "empresa_nome": company,
            }
        )

    centers: dict[tuple[str, int], dict[str, Any]] = {}
    for employee in employees:
        key = (employee["empresa_nome"], employee["centro_custo_num"])
        centers.setdefault(
            key,
            {
                "empresa": employee["empresa_nome"],
                "centro_id": employee["centro_custo_num"],
                "nome": employee["centro_custo"],
                "empregados": [],
            },
        )["empregados"].append(employee)

    return {
        "employees": employees,
        "invalid": invalid,
        "companies": sorted(companies),
        "source": source_path.name,
        "centros_de_custo": list(centers.values()),
        "empresa": fallback_company if len(companies) == 1 else None,
        "relatorio": "RELAÇÃO DE EMPREGADOS II",
        "centro_forcado": forced_center,
    }
