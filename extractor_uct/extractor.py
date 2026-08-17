# Extrai dados de colaboradores para a UCT.
# Biblioteca padrão.
import copy
import json
import time
from pathlib import Path

# Dependências externas.
import pandas as pd
import requests

# ============================================================
# CONFIGURAÇÕES
# ============================================================

POWERBI_URL = (
    "https://wabi-brazil-south-b-primary-api.analysis.windows.net/"
    "public/reports/querydata?synchronous=true"
)

RESOURCE_KEY = "d8467b9a-df1d-4bbc-a6d7-2b603c789861"

BASE_PAYLOAD_FILE = "base_payload.json"

OUTPUT_CSV = "colaboradores_powerbi.csv"
OUTPUT_XLSX = "colaboradores_powerbi.xlsx"

REQUEST_TIMEOUT = 120

# Pequeno intervalo entre queries.
REQUEST_DELAY = 0.10


HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json;charset=UTF-8",
    "x-powerbi-resourcekey": RESOURCE_KEY,
}


# ============================================================
# HELPERS DA SEMANTIC QUERY
# ============================================================


def column(source, entity, prop, name=None):
    return {
        "Column": {"Expression": {"SourceRef": {"Source": source}}, "Property": prop},
        "Name": name or f"{entity}.{prop}",
    }


def measure(source, entity, prop, name=None):
    return {
        "Measure": {"Expression": {"SourceRef": {"Source": source}}, "Property": prop},
        "Name": name or f"{entity}.{prop}",
    }


def equals_filter(source, prop, value):
    """
    Gera:
        campo = 'valor'

    no formato interno da SemanticQuery do Power BI.
    """

    value = str(value).replace("'", "''")

    return {
        "Condition": {
            "In": {
                "Expressions": [
                    {
                        "Column": {
                            "Expression": {"SourceRef": {"Source": source}},
                            "Property": prop,
                        }
                    }
                ],
                "Values": [[{"Literal": {"Value": f"'{value}'"}}]],
            }
        }
    }


# ============================================================
# BASE PAYLOAD
# ============================================================


def load_base_payload():
    path = Path(BASE_PAYLOAD_FILE)

    if not path.exists():
        raise FileNotFoundError(
            f"{BASE_PAYLOAD_FILE} não encontrado.\n"
            "Salve nele o Request Payload de uma chamada "
            "/public/reports/querydata do relatório."
        )

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_payload(base_payload, from_items, selects, where=None, count=5000):
    """
    Mantém os metadados do relatório/query original,
    mas substitui a Semantic Query.
    """

    payload = copy.deepcopy(base_payload)

    query_item = payload["queries"][0]

    # Evita reutilizar cache da query original.
    query_item.pop("CacheKey", None)
    query_item["QueryId"] = ""

    command = query_item["Query"]["Commands"][0]["SemanticQueryDataShapeCommand"]

    semantic_query = {"Version": 2, "From": from_items, "Select": selects}

    if where:
        semantic_query["Where"] = where

    command["Query"] = semantic_query

    command["Binding"] = {
        "Primary": {"Groupings": [{"Projections": list(range(len(selects)))}]},
        "DataReduction": {"DataVolume": 6, "Primary": {"Window": {"Count": count}}},
        "Version": 1,
    }

    command["ExecutionMetricsKind"] = 1

    return payload


# ============================================================
# REQUEST
# ============================================================


def execute(payload):
    response = requests.post(
        POWERBI_URL, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT
    )

    if not response.ok:
        print("\nERRO POWER BI")
        print("HTTP:", response.status_code)
        print(response.text[:5000])

        response.raise_for_status()

    result = response.json()

    # Algumas falhas do Power BI chegam dentro do JSON.
    if result.get("errors"):
        raise RuntimeError(json.dumps(result["errors"], indent=2, ensure_ascii=False))

    return result


# ============================================================
# DSR DECODER
# ============================================================


def get_data_node(response_json):
    return response_json["results"][0]["result"]["data"]


def get_dataset(response_json):
    data = get_data_node(response_json)

    return data["dsr"]["DS"][0]


def bit_is_set(mask, index):
    """
    R e Ø são bitmasks.

    Ex:
        R = 6 -> binário 00110

    indica quais posições reutilizam valor anterior.
    """

    return bool(mask & (1 << index))


def decode_rows(rows, value_dicts=None):
    """
    Decodifica linhas DSR do Power BI.

    Suporta:
      - G0/G1/G2... como propriedades diretas
      - C = valores compactados
      - R = bitmask de repetição
      - Ø = bitmask de NULL
      - DN = ValueDict
    """

    if not rows:
        return []

    value_dicts = value_dicts or {}

    schema = None
    previous = None
    decoded = []

    for raw in rows:

        if "S" in raw:
            schema = raw["S"]

        if schema is None:
            raise RuntimeError(f"Schema DSR não encontrado na linha: {raw}")

        column_count = len(schema)

        compact_values = raw.get("C", [])
        compact_index = 0

        repeat_mask = raw.get("R", 0)
        null_mask = raw.get("Ø", 0)

        current = []

        for i in range(column_count):

            definition = schema[i]

            field_name = definition.get("N")
            dict_name = definition.get("DN")

            # ------------------------------------------------
            # 1. Valor explícito como:
            #
            # "G0": "APUCARANA"
            # ------------------------------------------------

            if field_name in raw:
                value = raw[field_name]

            # ------------------------------------------------
            # 2. Valor repetido da linha anterior
            # ------------------------------------------------

            elif repeat_mask & (1 << i):

                if previous is not None:
                    value = previous[i]
                else:
                    value = None

            # ------------------------------------------------
            # 3. NULL
            # ------------------------------------------------

            elif null_mask & (1 << i):
                value = None

            # ------------------------------------------------
            # 4. Valor compactado em C
            # ------------------------------------------------

            else:

                if compact_index < len(compact_values):
                    value = compact_values[compact_index]
                    compact_index += 1
                else:
                    value = None

            # ------------------------------------------------
            # Resolve ValueDict
            #
            # Ex:
            # G0 = 2
            # DN = D0
            #
            # D0[2] = "DIRECAO DEFENSIVA"
            # ------------------------------------------------

            if (
                dict_name
                and value is not None
                and dict_name in value_dicts
                and isinstance(value, int)
            ):
                dictionary = value_dicts[dict_name]

                if 0 <= value < len(dictionary):
                    value = dictionary[value]

            current.append(value)

        decoded.append(current)
        previous = current

    return decoded


def find_dm_rows(ds):
    """
    Para nossas queries flat esperamos DM0.

    Mas procura dinamicamente caso o Power BI altere
    o número do Data Member.
    """

    ph = ds.get("PH", [])

    for item in ph:
        for key, value in item.items():

            if key.startswith("DM") and isinstance(value, list):
                return value

    return []


def response_to_rows(response_json):
    ds = get_dataset(response_json)

    rows = find_dm_rows(ds)

    value_dicts = ds.get("ValueDicts", {})

    return decode_rows(rows, value_dicts=value_dicts)


# ============================================================
# QUERY 1 — FILIAIS
# ============================================================


def get_branches(base_payload):
    payload = build_payload(
        base_payload=base_payload,
        from_items=[{"Name": "b", "Entity": "branch", "Type": 0}],
        selects=[column(source="b", entity="branch", prop="trade_name")],
        count=100,
    )

    response = execute(payload)

    rows = response_to_rows(response)

    branches = [row[0] for row in rows if row and row[0]]

    return sorted(set(branches))


# ============================================================
# QUERY 2 — DEPARTAMENTOS POR FILIAL
# ============================================================


def get_departments(base_payload, branch):
    payload = build_payload(
        base_payload=base_payload,
        from_items=[
            {"Name": "b", "Entity": "branch", "Type": 0},
            {"Name": "d", "Entity": "department", "Type": 0},
        ],
        selects=[column(source="d", entity="department", prop="name")],
        where=[equals_filter(source="b", prop="trade_name", value=branch)],
        count=5000,
    )

    response = execute(payload)

    rows = response_to_rows(response)

    departments = [row[0] for row in rows if row and row[0]]

    return sorted(set(departments))


# ============================================================
# QUERY 3 — COLABORADORES
# ============================================================


def get_employees(base_payload, branch, department):
    """
    Resultado esperado:

    filial
    departamento
    colaborador
    certificados_esperados
    certificados_concluidos
    certificados_pendentes
    """

    selects = [
        # Filial
        column(source="b", entity="branch", prop="trade_name"),
        # Departamento
        column(source="d", entity="department", prop="name"),
        # Colaborador
        column(source="u", entity="user", prop="first_name+last_name"),
        # Esperados
        measure(source="u", entity="user", prop="Certificados Esperados"),
        # Concluídos
        measure(
            source="u", entity="user", prop="quantidade usuarios concluiram trilha"
        ),
        # Pendentes
        measure(source="u", entity="user", prop="Pendentes"),
    ]

    payload = build_payload(
        base_payload=base_payload,
        from_items=[
            {"Name": "b", "Entity": "branch", "Type": 0},
            {"Name": "d", "Entity": "department", "Type": 0},
            {"Name": "u", "Entity": "user", "Type": 0},
        ],
        selects=selects,
        where=[
            equals_filter(source="b", prop="trade_name", value=branch),
            equals_filter(source="d", prop="name", value=department),
        ],
        count=5000,
    )

    response = execute(payload)

    rows = response_to_rows(response)

    result = []

    for row in rows:

        if len(row) < 6:
            continue

        result.append(
            {
                "filial": row[0],
                "departamento": row[1],
                "colaborador": row[2],
                "certificados_esperados": row[3],
                "certificados_concluidos": row[4],
                "certificados_pendentes": row[5],
            }
        )

    return result


# ============================================================
# MAIN
# ============================================================


def main():

    print("=" * 60)
    print("POWER BI EXTRACTOR")
    print("=" * 60)

    base_payload = load_base_payload()

    # --------------------------------------------------------
    # 1. Filiais
    # --------------------------------------------------------

    print("\nBuscando filiais...")

    branches = get_branches(base_payload)

    print(f"{len(branches)} filiais encontradas:")

    for branch in branches:
        print(" -", branch)

    all_employees = []

    # --------------------------------------------------------
    # 2. Filial -> Departamento
    # --------------------------------------------------------

    for branch_index, branch in enumerate(branches, start=1):

        print(f"\n[{branch_index}/{len(branches)}] " f"FILIAL: {branch}")

        try:
            departments = get_departments(base_payload, branch)

        except Exception as e:
            print(f"Erro buscando departamentos " f"de {branch}: {e}")
            continue

        print(f"  {len(departments)} departamentos.")

        # ----------------------------------------------------
        # 3. Departamento -> Colaboradores
        # ----------------------------------------------------

        for department_index, department in enumerate(departments, start=1):

            print(f"  [{department_index}/" f"{len(departments)}] " f"{department}")

            try:

                employees = get_employees(base_payload, branch, department)

                print(f"      {len(employees)} " f"colaboradores")

                all_employees.extend(employees)

            except Exception as e:

                print(f"      ERRO: {e}")

            time.sleep(REQUEST_DELAY)

    # --------------------------------------------------------
    # DataFrame
    # --------------------------------------------------------

    print("\nMontando DataFrame...")

    df = pd.DataFrame(all_employees)

    if df.empty:
        print("Nenhum colaborador retornado.")
        return

    # Evita linhas duplicadas caso o modelo gere
    # resultados repetidos.
    df = df.drop_duplicates()

    # Ordenação
    df = df.sort_values(
        by=["filial", "departamento", "colaborador"], na_position="last"
    )

    # --------------------------------------------------------
    # Export
    # --------------------------------------------------------

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    df.to_excel(OUTPUT_XLSX, index=False)

    print("\n" + "=" * 60)

    print(f"TOTAL: {len(df)} linhas")

    print(f"CSV:   {OUTPUT_CSV}")

    print(f"Excel: {OUTPUT_XLSX}")

    print("=" * 60)


if __name__ == "__main__":
    main()
