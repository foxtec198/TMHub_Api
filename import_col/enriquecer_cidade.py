"""
Adiciona cidade_id e cidade a cada funcionário, com base no centro_custo_num.
"""
import json

# --- Mapeamento cidade -> lista de centros de custo ---
CIDADES = {
    1: {"nome": "Londrina", "centros_custo": [28, 87, 92, 229, 231, 269, 286, 306, 308, 312]},
    2: {"nome": "Birigui", "centros_custo": [295]},
    3: {"nome": "Botucatu", "centros_custo": [296]},
    4: {"nome": "Ibiporã", "centros_custo": [101, 258]},
    5: {"nome": "Maringá", "centros_custo": [279]},
    6: {"nome": "Apucarana", "centros_custo": [76, 96]},
    7: {"nome": "Inativo", "centros_custo": [10, 24]},
}

# Índice reverso: centro_custo_num -> (cidade_id, cidade_nome)
CC_PARA_CIDADE = {}
for cidade_id, info in CIDADES.items():
    for cc in info["centros_custo"]:
        CC_PARA_CIDADE[cc] = (cidade_id, info["nome"])


def codigo_departamento(cc_num):
    """
    O centro_custo_num do relatorio é composto por: [codigo_departamento] + [sufixo de 3 digitos].
    Ex: 101001 -> departamento 101 ; 87001 -> departamento 87 ; 28000 -> departamento 28.
    Códigos com 3 dígitos ou menos (ex: 1, 2, 6) não têm departamento mapeável.
    """
    s = str(cc_num)
    if len(s) > 3:
        return int(s[:-3])
    return None


with open("funcionarios.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Centros de custo genéricos (sem sufixo de departamento) que também são Inativo
CC_GENERICOS_INATIVOS = {1, 2, 6}

sem_cidade = set()
for emp in data["empregados"]:
    try:
        cc_num = int(emp["centro_custo_num"])
    except (TypeError, ValueError):
        cc_num = None

    depto = codigo_departamento(cc_num) if cc_num is not None else None

    if depto in CC_PARA_CIDADE:
        cidade_id, cidade_nome = CC_PARA_CIDADE[depto]
        emp["departamento_codigo"] = depto
        emp["cidade_id"] = cidade_id
        emp["cidade"] = cidade_nome
    elif cc_num in CC_GENERICOS_INATIVOS:
        cidade_id, cidade_nome = CC_PARA_CIDADE[24]  # reaproveita o id da cidade "Inativo"
        emp["departamento_codigo"] = depto
        emp["cidade_id"] = cidade_id
        emp["cidade"] = cidade_nome
    else:
        emp["departamento_codigo"] = depto
        emp["cidade_id"] = None
        emp["cidade"] = None
        sem_cidade.add(depto)

# Adiciona a lista de cidades como referência no próprio JSON
data["cidades"] = [
    {"id": cid, "nome": info["nome"], "centros_custo": info["centros_custo"]}
    for cid, info in CIDADES.items()
]

with open("funcionarios.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Total de funcionários: {len(data['empregados'])}")
print(f"Centros de custo sem cidade mapeada: {sorted(c for c in sem_cidade if c is not None)}")
print(f"Funcionários sem cidade mapeada: {sum(1 for e in data['empregados'] if e['cidade_id'] is None)}")
