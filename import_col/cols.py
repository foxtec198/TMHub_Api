# Rotinas de importação de colaboradores: colunas da importação.
"""
Carrega o funcionarios.json (gerado a partir do relatório .htm de colaboradores),
achata a estrutura em uma lista única de empregados e enriquece cada um com
departamento_codigo, cidade_id e cidade — tudo em memória, sempre que o
módulo é importado. Não reescreve nada em disco.

Formato esperado de entrada (funcionarios.json):
{
  "centros_de_custo": [
    {
      "centro_de_custo": "1 - ZINATIVO",
      "empregados": [
        {
          "codigo": "4993", "nome": "...", "cargo": "...",
          "c_custo": "1", "hor": "220,00", "admissao": "18/03/2015",
          "situacao": "8", "cpf": "...", "salario": "..."
        },
        ...
      ]
    },
    ...
  ]
}

Saída (cols["empregados"][i]):
{
  ...todos os campos originais do funcionarios.json...,
  "centro_custo": "1 - ZINATIVO",
  "centro_custo_num": "1",
  "departamento_codigo": 101 | None,
  "cidade_id": 1 | None,
  "cidade": "Londrina" | None,
}
"""

# Biblioteca padrão.
import json
from os import getenv
from pathlib import Path

# Por padrão, procura funcionarios.json na mesma pasta deste arquivo (import_col/),
# independente de onde o comando "python ..." é executado. Pode ser sobrescrito
# via variável de ambiente FUNCIONARIOS_JSON_PATH no .env.
_DEFAULT_PATH = Path(__file__).resolve().parent / "funcionarios.json"
FUNCIONARIOS_JSON_PATH = getenv("FUNCIONARIOS_JSON_PATH", str(_DEFAULT_PATH))

# --- Mapeamento cidade -> lista de centros de custo ---
CIDADES = {
    1: {"nome": "Londrina", "centros_custo": [28, 44, 87, 92, 229, 231, 269, 286, 306, 308, 312]},
    2: {"nome": "Birigui", "centros_custo": [295]},
    3: {"nome": "Botucatu", "centros_custo": [296]},
    4: {"nome": "Ibiporã", "centros_custo": [101, 258]},
    5: {"nome": "Maringá", "centros_custo": [279]},
    6: {"nome": "Apucarana", "centros_custo": [76, 96]},
    7: {"nome": "Inativo", "centros_custo": [1, 2, 6, 10, 24]},
}

# Índice reverso: centro_custo/departamento -> (cidade_id, cidade_nome)
CC_PARA_CIDADE = {}
for _cidade_id, _info in CIDADES.items():
    for _cc in _info["centros_custo"]:
        CC_PARA_CIDADE[_cc] = (_cidade_id, _info["nome"])

# Centros de custo genéricos (sem sufixo de departamento) que também são Inativo
CC_GENERICOS_INATIVOS = {1, 2, 6}


def codigo_departamento(cc_num):
    """
    O centro_custo_num do relatório é composto por: [codigo_departamento] + [sufixo de 3 dígitos].
    Ex: 101001 -> departamento 101 ; 87001 -> departamento 87 ; 28000 -> departamento 28.
    Códigos com 3 dígitos ou menos (ex: 1, 2, 6) não têm departamento mapeável.
    """
    s = str(cc_num)
    if len(s) > 3:
        return int(s[:-3])
    return None


def _cidade_para(cc_num):
    """Retorna (departamento_codigo, cidade_id, cidade_nome) para um centro_custo_num."""
    try:
        cc_num_int = int(cc_num)
    except (TypeError, ValueError):
        return None, None, None

    depto = codigo_departamento(cc_num_int)

    if depto in CC_PARA_CIDADE:
        cidade_id, cidade_nome = CC_PARA_CIDADE[depto]
        return depto, cidade_id, cidade_nome
    if cc_num_int in CC_GENERICOS_INATIVOS:
        cidade_id, cidade_nome = CC_PARA_CIDADE[24]  # reaproveita o id da cidade "Inativo"
        return depto, cidade_id, cidade_nome
    return depto, None, None


def _load_cols(path: str = FUNCIONARIOS_JSON_PATH) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(
            f"Não encontrei o arquivo '{path}'. Defina FUNCIONARIOS_JSON_PATH "
            "no .env ou coloque o funcionarios.json nesse caminho."
        )

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    empregados = []
    for grupo in data.get("centros_de_custo", []):
        centro_custo = grupo.get("centro_de_custo")
        centro_custo_num = (
            centro_custo.split(" - ", 1)[0].strip() if centro_custo else None
        )
        depto, cidade_id, cidade_nome = _cidade_para(centro_custo_num)

        for emp in grupo.get("empregados", []):
            emp = dict(emp)  # copia para não alterar o dado original em memória
            emp["centro_custo"] = centro_custo
            emp["centro_custo_num"] = centro_custo_num
            emp["departamento_codigo"] = depto
            emp["cidade_id"] = cidade_id
            emp["cidade"] = cidade_nome
            empregados.append(emp)

    return {"empregados": empregados}


if __name__ == "__main__":
    cols = _load_cols()
    sem_cidade = {
        e["departamento_codigo"] for e in cols["empregados"] if e["cidade_id"] is None
    }
    print(f"Total de funcionários: {len(cols['empregados'])}")
    print(f"Centros de custo sem cidade mapeada: {sorted(c for c in sem_cidade if c is not None)}")
    print(f"Funcionários sem cidade mapeada: {sum(1 for e in cols['empregados'] if e['cidade_id'] is None)}")
