"""
Parser especializado para planilha de GLOSAS da prefeitura (centro de custo 87).

Estrutura da planilha:
  - Linha 0: cabeçalho principal
  - Linha 1: dias da semana / subtotais
  - Linha 2: datas (15=01/06 a 45=01/07)
  - Linha 3+: centros e funcionários

  Colunas:
    [0]  = ID do centro de custo | vazio
    [1]  = Tipo de posto (1- INS. 44H / 2- INS. 30H / 3- SIMPLES 44H)
    [2]  = Nome do colaborador
    [3]  = Data admissão
    [14] = Supervisor
    [15-45] = Dias do mês (faltas)
    [46] = TOTAL DE FALTAS
    [47] = Valor insalubre 44h
    [48] = Valor insalubre 30h
    [49] = Valor posto simples 44h48
    [51] = Vale transporte
"""

import re
from datetime import date, datetime
from decimal import Decimal
from os import path

import pandas as pd

from models.glosas import Disallowance
from utils.db import db

CENTRO_CUSTO_ID = 87
COMPETENCIA_ANO = 2026
COMPETENCIA_MES = 6


def _parse_nome_colaborador(raw: str) -> str:
    """Extrai apenas o nome do colaborador."""
    if not raw:
        return ""
    nome = raw.strip()
    nome = re.sub(r"^OK\s+", "", nome)
    nome = re.sub(r"\s+OK$", "", nome)
    nome = re.sub(r"\d{2}/\d{2}/\d{2,4}", "", nome)
    nome = re.sub(r"\d{4}-\d{2}-\d{2}", "", nome)
    return nome.strip()


def _parse_valor(raw) -> Decimal:
    """Converte para Decimal."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return Decimal("0")
    s = str(raw).strip().replace("R$", "").replace(" ", "")
    if not s or s == "nan":
        return Decimal("0")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return Decimal(str(float(s))).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0")


def _parse_qty(raw) -> Decimal:
    """Converte quantidade de faltas."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return Decimal("0")
    s = str(raw).strip()
    if not s or s == "nan":
        return Decimal("0")
    try:
        return Decimal(str(float(s)))
    except Exception:
        return Decimal("0")


def _is_employee(col1: str) -> bool:
    """Verifica se a linha é de funcionário."""
    return bool(re.search(r"\d-\s*(INS|SIMPLES)", str(col1)))



def _is_center(col0: str, col1: str) -> bool:
    """Verifica se a linha é de centro de custo."""
    return bool(col0.strip().isdigit()) and not _is_employee(col1) and bool(col1.strip())



def parse_planilha_glosas(filepath: str):
    """
    Lê a planilha de glosas e retorna lista de registros prontos para inserir.

    Returns:
        dict: {registros: [...], erros: [...], total_lidos: int}
    """
    df = pd.read_excel(filepath, header=None, dtype=str)

    # Datas dos dias (linha 2, colunas 15-45)
    dates_row = {}
    for col_idx in range(15, 46):
        raw = str(df.iloc[2, col_idx]) if pd.notna(df.iloc[2, col_idx]) else ""
        if raw and raw != "nan":
            try:
                dates_row[col_idx] = pd.to_datetime(raw).date()
            except Exception:
                pass

    current_centro_id = None
    registros = []
    erros = []

    for idx in range(3, len(df)):
        col0 = str(df.iloc[idx, 0]) if pd.notna(df.iloc[idx, 0]) else ""
        col1 = str(df.iloc[idx, 1]) if pd.notna(df.iloc[idx, 1]) else ""
        col2 = str(df.iloc[idx, 2]) if pd.notna(df.iloc[idx, 2]) else ""

        if not col0.strip() and not col1.strip() and not col2.strip():
            continue

        if _is_center(col0, col1):
            current_centro_id = int(col0.strip())
            continue

        if _is_employee(col1) and col2.strip():
            nome = _parse_nome_colaborador(col2)
            if not nome:
                continue

            total_faltas_raw = str(df.iloc[idx, 46]) if pd.notna(df.iloc[idx, 46]) else "0"
            total_faltas = _parse_qty(total_faltas_raw)
            if total_faltas <= 0:
                continue

            # Valor conforme tipo de posto
            if "30" in col1 and "INS" in col1:
                val_raw = str(df.iloc[idx, 48]) if pd.notna(df.iloc[idx, 48]) else "0"
            elif "INS" in col1:
                val_raw = str(df.iloc[idx, 47]) if pd.notna(df.iloc[idx, 47]) else "0"
            else:
                val_raw = str(df.iloc[idx, 49]) if pd.notna(df.iloc[idx, 49]) else "0"

            valor_glosa = _parse_valor(val_raw)
            if valor_glosa <= 0:
                continue

            try:
                valor_diaria = (valor_glosa / total_faltas).quantize(Decimal("0.01"))
            except Exception:
                valor_diaria = Decimal("180.00")

            for day_col in range(15, 46):
                falta_raw = str(df.iloc[idx, day_col]) if pd.notna(df.iloc[idx, day_col]) else ""
                falta_qty = _parse_qty(falta_raw)
                if falta_qty <= 0:
                    continue
                if not re.match(r"^\d*\.?\d+$", falta_raw.strip()):
                    continue

                dia_data = dates_row.get(day_col)
                if not dia_data:
                    continue

                proporcao = falta_qty / total_faltas if total_faltas > 0 else Decimal("0")
                valor_proporcional = (valor_glosa * proporcao).quantize(Decimal("0.01"))

                registros.append({
                    "competencia": date(COMPETENCIA_ANO, COMPETENCIA_MES, 1),
                    "data_falta": dia_data,
                    "centro_custo_id": current_centro_id or CENTRO_CUSTO_ID,
                    "colaborador_nome": nome,
                    "quantidade_dias": falta_qty,
                    "valor_diaria": valor_diaria,
                    "valor_total": valor_proporcional,
                    "cobertura": "em_analise",
                    "justificativa": f"Importado de {path.basename(filepath)}",
                })

    return {"registros": registros, "erros": erros, "total_lidos": len(registros)}


def importar_glosas(filepath: str):
    """Faz o parse e insere no banco."""
    resultado = parse_planilha_glosas(filepath)
    inseridos = 0
    erros_insercao = []

    for reg in resultado["registros"]:
        try:
            item = Disallowance(
                competencia=reg["competencia"],
                data_falta=reg["data_falta"],
                centro_custo_id=reg["centro_custo_id"],
                colaborador_nome=reg["colaborador_nome"],
                quantidade_dias=reg["quantidade_dias"],
                valor_diaria=reg["valor_diaria"],
                valor_total=reg["valor_total"],
                cobertura=reg["cobertura"],
                justificativa=reg["justificativa"],
            )
            db.session.add(item)
            inseridos += 1
        except Exception as e:
            erros_insercao.append(f"'{reg['colaborador_nome']}' dia {reg['data_falta']}: {str(e)}")

    db.session.commit()

    return {
        "inseridos": inseridos,
        "atualizados": 0,
        "erros": (resultado["erros"] + erros_insercao)[:50],
        "total_erros": len(resultado["erros"]) + len(erros_insercao),
        "total_lidos": resultado["total_lidos"],
    }

