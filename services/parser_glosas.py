"""Importação conciliada das glosas do departamento 87."""

import argparse
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from difflib import SequenceMatcher
from os import path

import pandas as pd

from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from models.controle_faltas import AbsenceControl
from models.glosas import Disallowance
from models.rp_historico import History
from utils.db import db


DEPARTAMENTO = 87
COMPETENCIA = date(2026, 6, 1)
DATE_COLUMNS = range(15, 46)


def _normalize(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


def _parse_employee_name(raw):
    name = str(raw or "").strip()
    name = re.sub(r"^OK\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+OK$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\d{2}/\d{2}/\d{2,4}", "", name)
    name = re.sub(r"\d{4}-\d{2}-\d{2}", "", name)
    name = re.sub(r"\s*/\s*.*$", "", name)
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    return re.sub(r"\s+", " ", name).strip(" -.")


def _decimal(raw):
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return Decimal("0")
    try:
        return Decimal(str(raw).replace(",", "."))
    except Exception:
        return Decimal("0")


def _is_employee(post_type):
    return bool(re.search(r"\d-\s*(INS|SIMPLES)", str(post_type or ""), re.IGNORECASE))


def parse_planilha_glosas(filepath):
    """Lê uma linha por colaborador e gera um registro para cada dia numérico."""
    frame = pd.read_excel(filepath, header=None, dtype=object)
    dates = {}
    for column in DATE_COLUMNS:
        value = frame.iloc[2, column]
        if pd.notna(value):
            parsed = pd.to_datetime(value).date()
            if parsed.year == COMPETENCIA.year and parsed.month == COMPETENCIA.month:
                dates[column] = parsed

    current_center_id = None
    current_center_name = None
    records = []
    errors = []

    for index in range(3, len(frame)):
        first = frame.iloc[index, 0] if pd.notna(frame.iloc[index, 0]) else None
        post_type = frame.iloc[index, 1] if pd.notna(frame.iloc[index, 1]) else ""
        raw_name = frame.iloc[index, 2] if pd.notna(frame.iloc[index, 2]) else ""

        if not _is_employee(post_type):
            try:
                center_id = int(first)
            except (TypeError, ValueError):
                center_id = None
            if center_id and str(post_type).strip():
                current_center_id = center_id
                current_center_name = str(post_type).strip()
            continue

        name = _parse_employee_name(raw_name)
        if not name:
            continue

        total_days = _decimal(frame.iloc[index, 46])
        if total_days <= 0:
            continue
        if "30" in str(post_type).upper() and "INS" in str(post_type).upper():
            total_value = _decimal(frame.iloc[index, 48])
        elif "INS" in str(post_type).upper():
            total_value = _decimal(frame.iloc[index, 47])
        else:
            total_value = _decimal(frame.iloc[index, 49])
        daily_value = (
            (total_value / total_days).quantize(Decimal("0.01"))
            if total_value > 0
            else Decimal("180.00")
        )

        for column, absence_date in dates.items():
            quantity = _decimal(frame.iloc[index, column])
            if quantity <= 0:
                continue
            records.append(
                {
                    "competencia": COMPETENCIA,
                    "data_falta": absence_date,
                    "centro_custo_id": current_center_id,
                    "centro_custo_nome": current_center_name,
                    "colaborador_nome": name,
                    "quantidade_dias": quantity.quantize(Decimal("0.0001")),
                    "valor_diaria": daily_value,
                    "linha_planilha": index + 1,
                    "tipo_posto": str(post_type).strip(),
                }
            )

    return {
        "registros": records,
        "erros": errors,
        "total_lidos": len(records),
        "total_dias": sum((item["quantidade_dias"] for item in records), Decimal("0")),
    }


def _best_fuzzy(target, candidates, threshold=0.90):
    ranked = sorted(
        (
            (SequenceMatcher(None, target, candidate).ratio(), candidate)
            for candidate in candidates
        ),
        reverse=True,
    )
    if not ranked or ranked[0][0] < threshold:
        return None
    if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < 0.04:
        return None
    return ranked[0][1]


def _center_tokens(value):
    ignored = {
        "ED",
        "LONDRINA",
        "E",
        "M",
        "EM",
        "CMEI",
        "ESCOLA",
        "MUNICIPAL",
        "PROF",
        "PROFESSOR",
        "PROFESSORA",
    }
    return {
        token
        for token in _normalize(value).split()
        if not token.isdigit() and token not in ignored
    }


def _resolve_center(sheet_name, centers, employee_name=None, employees=None):
    target_tokens = _center_tokens(sheet_name)
    if not target_tokens:
        return None
    target_text = " ".join(sorted(target_tokens))
    ranked = []
    for center in centers.values():
        candidate_tokens = _center_tokens(center.local)
        overlap = len(target_tokens & candidate_tokens)
        union = len(target_tokens | candidate_tokens)
        token_score = overlap / union if union else 0
        if target_tokens <= candidate_tokens or candidate_tokens <= target_tokens:
            token_score += 0.2
        text_score = SequenceMatcher(
            None, target_text, " ".join(sorted(candidate_tokens))
        ).ratio()
        score = max(token_score, text_score)
        ranked.append((score, center))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked or ranked[0][0] < 0.52:
        return None
    close = [center for score, center in ranked if ranked[0][0] - score < 0.08]
    if len(close) == 1:
        return close[0]

    if employee_name and employees:
        target_employee = _normalize(employee_name)
        employee_matches = []
        close_ids = {center.id for center in close}
        for employee in employees:
            if employee.centro_id not in close_ids:
                continue
            score = SequenceMatcher(
                None, target_employee, _normalize(employee.nome)
            ).ratio()
            employee_matches.append((score, employee.centro_id))
        employee_matches.sort(reverse=True)
        if employee_matches and employee_matches[0][0] >= 0.88:
            if (
                len(employee_matches) == 1
                or employee_matches[0][0] - employee_matches[1][0] >= 0.04
            ):
                return centers[employee_matches[0][1]]
    if len(close) > 1:
        return None
    return close[0]


def _coverage_for_history(history):
    if not history:
        return "em_analise"
    if history.status == "approved" and history.reserva_id:
        return "coberta"
    if history.status == "reproved":
        return "descoberta"
    return "em_analise"


def _values(quantity, daily_value, coverage):
    total = (quantity * daily_value).quantize(Decimal("0.01"))
    covered_days = quantity if coverage == "coberta" else Decimal("0")
    covered = (covered_days * daily_value).quantize(Decimal("0.01"))
    return covered_days, total, covered, (total - covered).quantize(Decimal("0.01"))


def importar_glosas(filepath, commit=True):
    """Concilia por colaborador + dia no histórico e importa sem duplicar."""
    parsed = parse_planilha_glosas(filepath)
    centers = {
        center.id: center
        for center in CostCenters.query.filter(CostCenters.departamento == DEPARTAMENTO).all()
    }
    employees = (
        Employees.query.join(CostCenters, CostCenters.id == Employees.centro_id)
        .filter(CostCenters.departamento == DEPARTAMENTO)
        .all()
    )
    employees_by_center_name = defaultdict(list)
    employees_by_name = defaultdict(list)
    for employee in employees:
        key = _normalize(employee.nome)
        employees_by_center_name[(employee.centro_id, key)].append(employee)
        employees_by_name[key].append(employee)

    histories = (
        db.session.query(History, Employees)
        .join(Employees, Employees.id == History.ausente_id)
        .join(CostCenters, CostCenters.id == History.cc)
        .filter(
            CostCenters.departamento == DEPARTAMENTO,
            History.created_at >= COMPETENCIA,
            History.created_at < date(COMPETENCIA.year, COMPETENCIA.month + 1, 1),
        )
        .order_by(History.id.desc())
        .all()
    )
    history_by_date_name = defaultdict(list)
    history_names_by_date = defaultdict(set)
    for history, employee in histories:
        history_date = history.created_at.date()
        name_key = _normalize(employee.nome)
        history_by_date_name[(history_date, name_key)].append((history, employee))
        history_names_by_date[history_date].add(name_key)

    absences = {
        absence.requisicao_id: absence
        for absence in AbsenceControl.query.filter(
            AbsenceControl.data_falta >= COMPETENCIA,
            AbsenceControl.data_falta < date(COMPETENCIA.year, COMPETENCIA.month + 1, 1),
        ).all()
    }
    existing_rows = Disallowance.query.filter(
        Disallowance.competencia == COMPETENCIA
    ).all()

    inserted = 0
    updated = 0
    skipped = 0
    matched_history = 0
    matched_employee = 0
    fuzzy_matches = 0
    pending_internal = 0
    issues = list(parsed["erros"])
    resolved_centers = {}

    for record in parsed["registros"]:
        target_name = _normalize(record["colaborador_nome"])
        sheet_center_key = (
            record["centro_custo_id"],
            _normalize(record["centro_custo_nome"]),
            target_name,
        )
        if sheet_center_key not in resolved_centers:
            resolved_centers[sheet_center_key] = _resolve_center(
                record["centro_custo_nome"],
                centers,
                employee_name=record["colaborador_nome"],
                employees=employees,
            )
        center = resolved_centers[sheet_center_key]
        if not center:
            issues.append(
                f"Linha {record['linha_planilha']}: contrato da planilha "
                f"{record['centro_custo_id']} ({record['centro_custo_nome']}) "
                "não foi localizado no departamento 87."
            )
            continue
        center_id = center.id

        candidates = history_by_date_name.get((record["data_falta"], target_name), [])
        if not candidates:
            fuzzy_name = _best_fuzzy(
                target_name, history_names_by_date.get(record["data_falta"], set())
            )
            if fuzzy_name:
                candidates = history_by_date_name[(record["data_falta"], fuzzy_name)]
                fuzzy_matches += 1
        if candidates:
            same_center = [item for item in candidates if item[0].cc == center_id]
            history, employee = (same_center or candidates)[0]
            matched_history += 1
        else:
            history = None
            employee_candidates = employees_by_center_name.get((center_id, target_name), [])
            if not employee_candidates:
                employee_candidates = employees_by_name.get(target_name, [])
            if not employee_candidates:
                center_names = {
                    name
                    for employee_center, name in employees_by_center_name
                    if employee_center == center_id
                }
                fuzzy_name = _best_fuzzy(target_name, center_names)
                if fuzzy_name:
                    employee_candidates = employees_by_center_name[(center_id, fuzzy_name)]
                    fuzzy_matches += 1
            employee = employee_candidates[0] if len(employee_candidates) == 1 else None
            if employee:
                matched_employee += 1
            pending_internal += 1

        absence = absences.get(history.requisicao_id) if history else None
        coverage = _coverage_for_history(history)
        covered_days, total, covered, uncovered = _values(
            record["quantidade_dias"], record["valor_diaria"], coverage
        )
        existing = None
        if absence:
            existing = next(
                (item for item in existing_rows if item.falta_id == absence.id), None
            )
        if not existing:
            existing = next(
                (
                    item
                    for item in existing_rows
                    if item.data_falta == record["data_falta"]
                    and item.centro_custo_id == center_id
                    and (
                        (employee and item.colaborador_id == employee.id)
                        or (
                            not item.colaborador_id
                            and _normalize(item.colaborador_nome) == target_name
                        )
                    )
                ),
                None,
            )

        item = existing or Disallowance()
        if existing and existing.evidencia_arquivo:
            skipped += 1
            continue
        item.competencia = COMPETENCIA
        item.data_falta = record["data_falta"]
        item.centro_custo_id = center_id
        item.colaborador_id = employee.id if employee else None
        item.colaborador_nome = employee.nome if employee else record["colaborador_nome"]
        item.colaborador_matricula = str(employee.matricula) if employee else None
        item.falta_id = absence.id if absence else None
        item.requisicao_id = history.requisicao_id if history else None
        item.cobertura = coverage
        item.quantidade_dias = record["quantidade_dias"]
        item.quantidade_coberta_dias = covered_days
        item.valor_diaria = record["valor_diaria"]
        item.valor_total = total
        item.valor_coberto = covered
        item.valor_descoberto = uncovered
        item.justificativa = (
            f"Importada de {path.basename(filepath)}. "
            + (
                f"Conciliada com a requisição #{history.requisicao_id}."
                if history
                else "Não localizada no histórico; pendente de tratativa interna."
            )
        )
        item.observacao = (
            f"Planilha do departamento 87, linha {record['linha_planilha']}; "
            f"contrato informado: {record['centro_custo_nome']} "
            f"(referência {record['centro_custo_id']})."
        )
        if existing:
            updated += 1
        else:
            db.session.add(item)
            existing_rows.append(item)
            inserted += 1

    if commit:
        db.session.commit()
    else:
        db.session.rollback()

    return {
        "inseridos": inserted,
        "atualizados": updated,
        "ignorados_com_evidencia": skipped,
        "conciliados_historico": matched_history,
        "somente_colaborador": matched_employee,
        "pendentes_tratativa_interna": pending_internal,
        "correspondencias_aproximadas": fuzzy_matches,
        "erros": issues,
        "total_erros": len(issues),
        "total_lidos": parsed["total_lidos"],
        "total_dias": str(parsed["total_dias"]),
        "gravado": commit,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("arquivo")
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Grava no banco. Sem esta opção, apenas simula e reverte.",
    )
    args = parser.parse_args()

    from app import app

    with app.app_context():
        result = importar_glosas(args.arquivo, commit=args.commit)
    for key, value in result.items():
        if key != "erros":
            print(f"{key}: {value}")
    for error in result["erros"][:50]:
        print(f"erro: {error}")


if __name__ == "__main__":
    main()
