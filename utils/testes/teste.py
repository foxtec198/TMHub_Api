import re
import unicodedata
import pprint
from rapidfuzz import fuzz, process as rf_process

from utils.testes.historico_output import historico

COLAB_FILE = "colaboradores_raw.txt"
FUZZY_THRESHOLD = 88  # abaixo disso, não linka automaticamente


def strip_accents(s):
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize(name):
    if not name:
        return ""
    n = strip_accents(name).upper()
    n = re.sub(r"[^A-Z\s]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def load_colaboradores(path):
    colabs = {}  # id -> nome original
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            cid, nome = line.split("\t", 1)
            colabs[cid.strip()] = nome.strip()
    return colabs


def build_lookup(colabs):
    # nome normalizado -> lista de (id, nome_original)
    lookup = {}
    for cid, nome in colabs.items():
        norm = normalize(nome)
        lookup.setdefault(norm, []).append((cid, nome))
    return lookup


def match_name(name, lookup, norm_choices):
    """Retorna (id, nome_colaborador, score) ou (None, None, 0)."""
    if not name:
        return None, None, 0

    norm = normalize(name)
    if not norm:
        return None, None, 0

    # 1. match exato
    if norm in lookup:
        cid, nome = lookup[norm][0]
        return cid, nome, 100

    # 2. fuzzy match
    result = rf_process.extractOne(
        norm, norm_choices, scorer=fuzz.token_sort_ratio
    )
    if result is None:
        return None, None, 0

    best_norm, score, _ = result
    if score >= FUZZY_THRESHOLD:
        cid, nome = lookup[best_norm][0]
        return cid, nome, score

    return None, None, score


def process():
    colabs = load_colaboradores(COLAB_FILE)
    lookup = build_lookup(colabs)
    norm_choices = list(lookup.keys())

    not_found = {}  # nome_original -> {"campo": [...], "melhor_tentativa": (nome, score)}
    linked = []

    for rec in historico:
        new_rec = dict(rec)

        for campo, id_campo in (("ausente", "ausente_id"), ("reserva", "reserva_id")):
            valor = rec.get(campo)
            if not valor:
                new_rec[id_campo] = None
                continue

            cid, nome_colab, score = match_name(valor, lookup, norm_choices)
            new_rec[id_campo] = int(cid) if cid is not None else None

            if cid is None:
                entry = not_found.setdefault(valor, {"campos": set(), "melhor_tentativa": None, "score": 0})
                entry["campos"].add(campo)
                # guarda a melhor tentativa mesmo que abaixo do threshold, pra ajudar na revisão manual
                norm = normalize(valor)
                if norm:
                    res = rf_process.extractOne(norm, norm_choices, scorer=fuzz.token_sort_ratio)
                    if res:
                        best_norm, sc, _ = res
                        cand_id, cand_nome = lookup[best_norm][0]
                        if sc > entry["score"]:
                            entry["score"] = sc
                            entry["melhor_tentativa"] = (cand_id, cand_nome, sc)

        linked.append(new_rec)

    not_found_list = []
    for nome, info in sorted(not_found.items()):
        not_found_list.append({
            "nome_planilha": nome,
            "campos": sorted(info["campos"]),
            "sugestao_id": info["melhor_tentativa"][0] if info["melhor_tentativa"] else None,
            "sugestao_nome": info["melhor_tentativa"][1] if info["melhor_tentativa"] else None,
            "sugestao_score": info["melhor_tentativa"][2] if info["melhor_tentativa"] else None,
        })

    return linked, not_found_list


if __name__ == "__main__":
    linked, not_found_list = process()

    print(f"Total de registros: {len(linked)}")
    print(f"Nomes nao encontrados (unicos): {len(not_found_list)}")
    print()
    pprint.pprint(not_found_list)

    with open("history.py", "w", encoding="utf-8") as f:
        f.write("historico = ")
        f.write(pprint.pformat(linked, width=100, sort_dicts=False))
        f.write("\n\nnao_encontrados = ")
        f.write(pprint.pformat(not_found_list, width=100, sort_dicts=False))
        f.write("\n")