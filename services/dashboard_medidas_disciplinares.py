from collections import defaultdict
from datetime import date, datetime

from flask import jsonify, request
from sqlalchemy import String, cast

from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from models.controle_faltas import AbsenceControl
from models.medidas_disciplinares import DisciplinaryMeasure
from models.supervisores import Supervisors
from services.medidas_disciplinares import MEASURE_TYPES, reason_label
from utils.db import db
from utils.filial_scope import apply_cost_center_scope
from utils.permissions import has_permission
from utils.safe_route import safe_route


ORIGIN_LABELS = {
    "manual": "Manual",
    "importacao": "Planilha",
}


def _parse_date(value, field):
    try:
        return datetime.strptime(str(value or "").strip(), "%Y-%m-%d").date()
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} inválida; use aaaa-mm-dd.") from error


def _period():
    today = date.today()
    start = (
        _parse_date(request.args.get("inicio"), "Data inicial")
        if request.args.get("inicio")
        else date(today.year, 1, 1)
    )
    end = (
        _parse_date(request.args.get("fim"), "Data final")
        if request.args.get("fim")
        else today
    )
    if start > end:
        raise ValueError("A data inicial não pode ser posterior à data final.")
    return start, end


def _csv_values(name):
    return {
        value.strip()
        for value in str(request.args.get(name) or "").split(",")
        if value.strip()
    }


def _integer_values(name):
    values = _csv_values(name)
    try:
        return {int(value) for value in values}
    except ValueError as error:
        raise ValueError(f"Filtro de {name} inválido.") from error


def _month_keys(start, end):
    keys = []
    cursor = date(start.year, start.month, 1)
    limit = date(end.year, end.month, 1)
    while cursor <= limit:
        keys.append(cursor.strftime("%Y-%m"))
        cursor = date(
            cursor.year + (1 if cursor.month == 12 else 0),
            1 if cursor.month == 12 else cursor.month + 1,
            1,
        )
    return keys


def _filter_options(rows):
    collaborators = {}
    departments = set()
    cost_centers = {}
    supervisors = set()
    reasons = {}
    origins = set()

    for row in rows:
        measure = row[0]
        collaborators[row.colaborador_id] = {
            "value": str(row.colaborador_id),
            "label": (
                f"{row.colaborador_nome or 'Sem nome'} · "
                f"{row.matricula or 'Sem matrícula'}"
            ),
        }
        if row.departamento is not None:
            departments.add(row.departamento)
        if row.centro_custo_id is not None:
            cost_centers[row.centro_custo_id] = {
                "value": str(row.centro_custo_id),
                "label": (
                    f"{row.centro_custo_id} - "
                    f"{row.contrato or 'Sem identificação'}"
                ),
            }
        if measure.supervisor_nome:
            supervisors.add(measure.supervisor_nome)
        if measure.motivo:
            reasons[measure.motivo] = reason_label(
                measure.motivo,
                measure.motivo_detalhe,
            )
        if measure.origem:
            origins.add(measure.origem)

    return {
        "departamentos": [
            {"value": str(value), "label": f"DPTO. {value}"}
            for value in sorted(departments)
        ],
        "centros_custo": sorted(
            cost_centers.values(),
            key=lambda item: item["label"].casefold(),
        ),
        "supervisores": [
            {"value": value, "label": value}
            for value in sorted(supervisors, key=str.casefold)
        ],
        "colaboradores": sorted(
            collaborators.values(),
            key=lambda item: item["label"].casefold(),
        ),
        "tipos": [
            {"value": value, "label": label}
            for value, label in MEASURE_TYPES.items()
        ],
        "motivos": sorted(
            [
                {"value": value, "label": label}
                for value, label in reasons.items()
            ],
            key=lambda item: item["label"].casefold(),
        ),
        "origens": [
            {"value": value, "label": ORIGIN_LABELS.get(value, value)}
            for value in sorted(origins, key=str.casefold)
        ],
    }


class DisciplinaryMeasuresDashboardService:
    @safe_route
    def read(self, token_data):
        try:
            start, end = _period()
            collaborators = _integer_values("colaborador")
            cost_centers = _integer_values("centro_custo")
        except ValueError as error:
            return jsonify(str(error)), 400

        departments = _csv_values("departamento")
        supervisors = _csv_values("supervisor")
        measure_types = _csv_values("tipo")
        reasons = _csv_values("motivo")
        origins = _csv_values("origem")

        base_query = (
            db.session.query(
                DisciplinaryMeasure,
                Employees.id.label("colaborador_id"),
                Employees.matricula.label("matricula"),
                Employees.nome.label("colaborador_nome"),
                Employees.centro_id.label("centro_custo_id"),
                Employees.situacao.label("situacao_colaborador"),
                CostCenters.local.label("contrato"),
                CostCenters.departamento.label("departamento"),
                Supervisors.nome.label("supervisor_local"),
            )
            .join(Employees, Employees.id == DisciplinaryMeasure.colaborador_id)
            .outerjoin(CostCenters, CostCenters.id == Employees.centro_id)
            .outerjoin(Supervisors, Supervisors.id == CostCenters.supervisor_id)
            .filter(DisciplinaryMeasure.data_medida.between(start, end))
        )
        base_query = apply_cost_center_scope(
            base_query,
            Employees.centro_id,
            token_data,
        )

        # Opções, indicadores, gráficos e registros partem do mesmo escopo seguro.
        option_rows = base_query.all()
        options = _filter_options(option_rows)
        query = base_query

        # Advertencia e a metrica fixa deste comparativo. O filtro de tipo nao
        # remove a serie; todos os demais filtros compativeis continuam ativos.
        comparison_measure_rows = [
            row
            for row in option_rows
            if row[0].tipo == "advertencia"
            and (not departments or str(row.departamento) in departments)
            and (not cost_centers or row.centro_custo_id in cost_centers)
            and (not collaborators or row.colaborador_id in collaborators)
            and (not reasons or row[0].motivo in reasons)
            and (not origins or row[0].origem in origins)
        ]

        if departments:
            query = query.filter(
                cast(CostCenters.departamento, String).in_(departments)
            )
        if cost_centers:
            query = query.filter(Employees.centro_id.in_(cost_centers))
        if supervisors:
            query = query.filter(
                DisciplinaryMeasure.supervisor_nome.in_(supervisors)
            )
        if collaborators:
            query = query.filter(
                DisciplinaryMeasure.colaborador_id.in_(collaborators)
            )
        if measure_types:
            query = query.filter(DisciplinaryMeasure.tipo.in_(measure_types))
        if reasons:
            query = query.filter(DisciplinaryMeasure.motivo.in_(reasons))
        if origins:
            query = query.filter(DisciplinaryMeasure.origem.in_(origins))

        rows = query.order_by(
            DisciplinaryMeasure.data_medida.desc(),
            DisciplinaryMeasure.id.desc(),
        ).all()

        monthly = {
            key: {
                "mes": key,
                "total": 0,
                "advertencias": 0,
                "suspensoes": 0,
                "dias_suspensao": 0,
            }
            for key in _month_keys(start, end)
        }
        type_counts = defaultdict(int)
        reason_counts = defaultdict(int)
        department_counts = defaultdict(
            lambda: {"total": 0, "advertencias": 0, "suspensoes": 0}
        )
        supervisor_counts = defaultdict(
            lambda: {"total": 0, "advertencias": 0, "suspensoes": 0}
        )
        offender_counts = {}
        indicators = {
            "total": len(rows),
            "advertencias": 0,
            "suspensoes": 0,
            "colaboradores": 0,
            "dias_suspensao": 0,
        }
        collaborator_ids = set()

        for row in rows:
            measure = row[0]
            collaborator_ids.add(measure.colaborador_id)
            type_key = (
                "advertencias"
                if measure.tipo == "advertencia"
                else "suspensoes"
            )
            indicators[type_key] += 1
            type_counts[measure.tipo] += 1
            if measure.tipo == "suspensao":
                suspension_days = int(measure.quantidade_dias or 0)
                indicators["dias_suspensao"] += suspension_days
            else:
                suspension_days = 0

            month = monthly[measure.data_medida.strftime("%Y-%m")]
            month["total"] += 1
            month[type_key] += 1
            month["dias_suspensao"] += suspension_days

            reason = reason_label(measure.motivo, measure.motivo_detalhe)
            reason_counts[reason] += 1
            department = (
                f"DPTO. {row.departamento}"
                if row.departamento is not None
                else "Sem departamento"
            )
            department_counts[department]["total"] += 1
            department_counts[department][type_key] += 1
            supervisor = measure.supervisor_nome or "Sem supervisor"
            supervisor_counts[supervisor]["total"] += 1
            supervisor_counts[supervisor][type_key] += 1

            # Situacao 1 e a regra adotada pelo projeto para colaborador ativo.
            if row.situacao_colaborador == 1:
                offender = offender_counts.setdefault(
                    measure.colaborador_id,
                    {
                        "colaborador_id": measure.colaborador_id,
                        "colaborador": row.colaborador_nome or "Sem identificação",
                        "matricula": row.matricula,
                        "contrato": row.contrato or "Sem contrato",
                        "departamento": department,
                        "total": 0,
                        "advertencias": 0,
                        "suspensoes": 0,
                    },
                )
                offender["total"] += 1
                offender[type_key] += 1

        indicators["colaboradores"] = len(collaborator_ids)
        total = indicators["total"]
        type_list = [
            {
                "tipo": measure_type,
                "label": label,
                "total": type_counts[measure_type],
                "percentual": (
                    round(type_counts[measure_type] * 100 / total, 1)
                    if total
                    else 0
                ),
            }
            for measure_type, label in MEASURE_TYPES.items()
        ]
        reason_list = [
            {
                "label": label,
                "total": count,
                "percentual": round(count * 100 / total, 1) if total else 0,
            }
            for label, count in reason_counts.items()
        ]
        reason_list.sort(
            key=lambda item: (-item["total"], item["label"].casefold())
        )
        department_list = [
            {"label": label, **values}
            for label, values in department_counts.items()
        ]
        department_list.sort(
            key=lambda item: (-item["total"], item["label"].casefold())
        )
        supervisor_list = [
            {"label": label, **values}
            for label, values in supervisor_counts.items()
        ]
        supervisor_list.sort(
            key=lambda item: (-item["total"], item["label"].casefold())
        )
        offender_list = sorted(
            offender_counts.values(),
            key=lambda item: (
                -item["total"],
                -item["suspensoes"],
                item["colaborador"].casefold(),
            ),
        )[:10]

        single_cost_center = len(cost_centers) == 1
        absence_comparison = {
            "autorizado": False,
            "nivel": "centro_custo" if single_cost_center else "departamento",
            "centro_custo": None,
            "supervisor": None,
            "itens": [],
        }
        can_view_absences = (
            has_permission(token_data, "dashboard_faltas", "view")
            or has_permission(token_data, "controle_faltas", "view")
        )
        if can_view_absences:
            warning_counts = defaultdict(int)
            group_details = {}

            def group_data(row):
                center_name = (
                    getattr(row, "contrato", None)
                    or getattr(row, "centro_custo", None)
                    or "Sem centro de custo"
                )
                if single_cost_center:
                    key = f"centro:{row.centro_custo_id}"
                    details = {
                        "label": center_name,
                        "departamento": (
                            f"DPTO. {row.departamento}"
                            if row.departamento is not None
                            else "Sem departamento"
                        ),
                        "centro_custo_id": row.centro_custo_id,
                        "centro_custo": center_name,
                        "supervisor": row.supervisor_local or "Sem supervisor",
                    }
                    return key, details

                department = (
                    f"DPTO. {row.departamento}"
                    if row.departamento is not None
                    else "Sem departamento"
                )
                return f"departamento:{department}", {
                    "label": department,
                    "departamento": department,
                    "centro_custo_id": None,
                    "centro_custo": None,
                    "supervisor": None,
                }

            selected_center_details = {}
            if single_cost_center:
                selected_center_id = next(iter(cost_centers))
                selected_center_row = next(
                    (
                        row
                        for row in option_rows
                        if row.centro_custo_id == selected_center_id
                    ),
                    None,
                )
                if selected_center_row is not None:
                    _, selected_center_details = group_data(selected_center_row)

            for row in comparison_measure_rows:
                if row.centro_custo_id is None:
                    continue
                group_key, details = group_data(row)
                warning_counts[group_key] += 1
                group_details[group_key] = details

            absence_query = (
                db.session.query(
                    AbsenceControl.centro_custo_id,
                    CostCenters.local.label("centro_custo"),
                    CostCenters.departamento.label("departamento"),
                    Supervisors.nome.label("supervisor_local"),
                    db.func.count(AbsenceControl.id).label("faltas_injustificadas"),
                )
                .select_from(AbsenceControl)
                .join(CostCenters, CostCenters.id == AbsenceControl.centro_custo_id)
                .outerjoin(Supervisors, Supervisors.id == CostCenters.supervisor_id)
                .filter(AbsenceControl.classificacao == "injustificada")
                .filter(
                    AbsenceControl.data_falta.between(
                        datetime.combine(start, datetime.min.time()),
                        datetime.combine(end, datetime.max.time()),
                    )
                )
            )
            absence_query = apply_cost_center_scope(
                absence_query,
                AbsenceControl.centro_custo_id,
                token_data,
            )
            if departments:
                absence_query = absence_query.filter(
                    cast(CostCenters.departamento, String).in_(departments)
                )
            if cost_centers:
                absence_query = absence_query.filter(
                    AbsenceControl.centro_custo_id.in_(cost_centers)
                )
            if collaborators:
                absence_query = absence_query.filter(
                    AbsenceControl.colaborador_id.in_(collaborators)
                )

            absence_rows = absence_query.group_by(
                AbsenceControl.centro_custo_id,
                CostCenters.local,
                CostCenters.departamento,
                Supervisors.nome,
            ).all()
            absence_counts = defaultdict(int)
            for row in absence_rows:
                group_key, details = group_data(row)
                absence_counts[group_key] += int(row.faltas_injustificadas or 0)
                group_details[group_key] = details

            comparison_items = [
                {
                    **group_details[group_key],
                    "faltas_injustificadas": absence_counts.get(group_key, 0),
                    "advertencias": warning_counts.get(group_key, 0),
                }
                for group_key in set(absence_counts) | set(warning_counts)
            ]
            comparison_items.sort(
                key=lambda item: (
                    -item["faltas_injustificadas"],
                    -item["advertencias"],
                    item["label"].casefold(),
                )
            )
            selected_details = (
                comparison_items[0]
                if single_cost_center and comparison_items
                else selected_center_details
            )
            absence_comparison = {
                "autorizado": True,
                "nivel": "centro_custo" if single_cost_center else "departamento",
                "centro_custo": selected_details.get("centro_custo"),
                "supervisor": selected_details.get("supervisor"),
                "itens": comparison_items,
            }

        return jsonify({
            "periodo": {"inicio": start.isoformat(), "fim": end.isoformat()},
            "indicadores": indicators,
            "mensal": list(monthly.values()),
            "tipos": type_list,
            "motivos": reason_list,
            "departamentos": department_list,
            "supervisores": supervisor_list,
            "maiores_ofensores": offender_list,
            "comparativo_faltas": absence_comparison,
            "filtros": options,
        }), 200
