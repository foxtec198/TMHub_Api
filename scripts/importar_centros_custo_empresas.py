"""Sincroniza centros de custo separados por empresa.

Recebe um JSON já extraído de relatórios de centros de custo e usa a chave
``empresa + numero``. Linhas sem código/nome são ignoradas e registros antigos
sem nome ou local são removidos antes da sincronização.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from os import getenv


def normalize_company(value):
    return " ".join(str(value or "").strip().split()).upper()


def load_payload(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("O arquivo deve conter uma lista de empresas.")
    companies = []
    for entry in payload:
        company_name = normalize_company(entry.get("empresa"))
        centers = entry.get("centros") or []
        if not company_name:
            raise ValueError("Uma empresa do arquivo não possui nome.")
        normalized_centers = {}
        for item in centers:
            try:
                number = int(item.get("numero"))
            except (TypeError, ValueError):
                continue
            name = " ".join(str(item.get("nome") or "").strip().split()).upper()
            if number <= 0 or not name:
                continue
            previous = normalized_centers.get(number)
            if previous and previous != name:
                raise ValueError(
                    f"Empresa {company_name}: o código {number} possui nomes conflitantes."
                )
            normalized_centers[number] = name
        companies.append((company_name, normalized_centers))
    return companies


def sync(companies):
    engine = create_engine(getenv("DB_URI"))
    with engine.begin() as connection:
        removed = connection.execute(text("""
            DELETE FROM centro_de_custo
            WHERE nome IS NULL OR trim(nome) = '' OR local IS NULL OR trim(local) = ''
        """)).rowcount
        company_ids = {
            row.nome: row.id
            for row in connection.execute(text("SELECT id, nome FROM empresas")).mappings()
        }
        created_companies = 0
        created = updated = 0
        statement = text("""
            INSERT INTO centro_de_custo (empresa_id, centro_id, nome, local)
            VALUES (:empresa_id, :centro_id, :nome, :local)
            ON CONFLICT (empresa_id, centro_id) DO UPDATE
            SET nome = EXCLUDED.nome, local = EXCLUDED.local
            RETURNING (xmax = 0) AS inserted
        """)
        for company_name, centers in companies:
            company_id = company_ids.get(company_name)
            if company_id is None:
                company_id = connection.execute(
                    text("INSERT INTO empresas (nome, ativa) VALUES (:nome, TRUE) RETURNING id"),
                    {"nome": company_name},
                ).scalar_one()
                company_ids[company_name] = company_id
                created_companies += 1
            for number, name in centers.items():
                result = connection.execute(statement, {
                    "empresa_id": company_id,
                    "centro_id": number,
                    "nome": name,
                    "local": name,
                }).scalar_one()
                created += int(result)
                updated += int(not result)
    return {
        "empresas_processadas": len(companies),
        "empresas_criadas": created_companies,
        "centros_criados": created,
        "centros_atualizados": updated,
        "centros_removidos_sem_nome_ou_local": removed,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("arquivo", type=Path, help="JSON de centros separados por empresa")
    args = parser.parse_args()
    load_dotenv()
    print(json.dumps(sync(load_payload(args.arquivo)), ensure_ascii=False))


if __name__ == "__main__":
    main()
