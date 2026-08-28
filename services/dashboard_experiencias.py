# Regras de negócio do dashboard de avaliações de experiência.
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from flask import jsonify, request

from models.avaliacoes_experiencia import ExperienceEvaluation
from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from models.usuarios import Users
from utils.filial_scope import apply_cost_center_scope
from utils.permissions import has_permission
from utils.safe_route import safe_route


STATUS_LABELS = {
    "aberta": "Aberta",
    "em_preenchimento": "Em preenchimento",
    "aguardando_rh": "Aguardando RH",
    "atrasada": "Atrasada",
    "concluida": "Concluída",
    "cancelada": "Cancelada",
}
OPEN_STATUSES = {"aberta", "em_preenchimento", "atrasada"}
DECISION_LABELS = {
    "demitir": "Demitir",
    "efetivar": "Efetivar",
    "prorrogar": "Prorrogar",
}


def _date_value(value, label):
    """Converte um filtro ISO em data e devolve erro previsível quando inválido."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError(f"{label} deve usar o formato AAAA-MM-DD.") from error


def _integer_values(name):
    """Lê listas separadas por vírgula sem aceitar valores inválidos silenciosamente."""
    raw_value = str(request.args.get(name) or "").strip()
    if not raw_value:
        return []
    try:
        return [int(value) for value in raw_value.split(",") if value.strip()]
    except ValueError as error:
        raise ValueError(f"O filtro {name} possui um valor inválido.") from error


def _status_values():
    """Normaliza as situações permitidas pelo modelo para uso nos filtros."""
    return [
        value
        for value in str(request.args.get("status") or "").split(",")
        if value in STATUS_LABELS
    ]


def _month_keys(start, end):
    """Gera todos os meses do período para o gráfico não omitir meses vazios."""
    cursor = start.replace(day=1)
    last = end.replace(day=1)
    keys = []
    while cursor <= last:
        keys.append(cursor.strftime("%Y-%m"))
        cursor = (
            cursor.replace(year=cursor.year + 1, month=1)
            if cursor.month == 12
            else cursor.replace(month=cursor.month + 1)
        )
    return keys


class ExperienceDashboardService:
    """Consolida a fila de experiência em indicadores seguros por filial."""

    @staticmethod
    def _filters():
        try:
            start = _date_value(request.args.get("inicio"), "A data inicial")
            end = _date_value(request.args.get("fim"), "A data final")
            if start and end and start > end:
                raise ValueError("A data inicial não pode ser posterior à data final.")
            return {
                "start": start,
                "end": end,
                "departments": _integer_values("departamento"),
                "cost_centers": _integer_values("centro_custo"),
                "supervisors": _integer_values("supervisor"),
                "statuses": _status_values(),
            }, None
        except ValueError as error:
            return None, error

    @staticmethod
    def _filter_options(rows):
        """Monta opções somente com dados que o usuário já pode consultar."""
        departments = sorted({
            str(row.departamento)
            for row in rows
            if row.departamento is not None
        }, key=int)
        cost_centers = {
            row.centro_custo_id: row.centro_custo
            for row in rows
            if row.centro_custo_id is not None and row.centro_custo
        }
        supervisors = {
            row.ExperienceEvaluation.supervisor_usuario_id: row.supervisor
            for row in rows
            if row.ExperienceEvaluation.supervisor_usuario_id is not None and row.supervisor
        }
        return {
            "departamentos": [
                {"value": value, "label": f"DPTO. {value}"}
                for value in departments
            ],
            "centros_custo": [
                {"value": center_id, "label": name}
                for center_id, name in sorted(
                    cost_centers.items(),
                    key=lambda item: item[1].casefold(),
                )
            ],
            "supervisores": [
                {"value": supervisor_id, "label": name}
                for supervisor_id, name in sorted(
                    supervisors.items(),
                    key=lambda item: item[1].casefold(),
                )
            ],
            "situacoes": [
                {"value": value, "label": label}
                for value, label in STATUS_LABELS.items()
                if any(
                    row.ExperienceEvaluation.status == value
                    for row in rows
                )
            ],
        }

    @safe_route
    def read(self, token_data):
        """Retorna os indicadores, gráficos e filas do dashboard de experiência."""
        if not has_permission(token_data, "controle_experiencia_rh", "view"):
            return jsonify("Você não possui acesso ao dashboard de experiência."), 403

        filters, error = self._filters()
        if error:
            return jsonify(str(error)), 400

        base_query = (
            ExperienceEvaluation.query
            .join(Employees, Employees.id == ExperienceEvaluation.colaborador_id)
            .outerjoin(CostCenters, CostCenters.id == Employees.centro_id)
            .outerjoin(Users, Users.id == ExperienceEvaluation.supervisor_usuario_id)
            .with_entities(
                ExperienceEvaluation,
                Employees.nome.label("colaborador_nome"),
                Employees.matricula.label("matricula"),
                Employees.centro_id.label("centro_custo_id"),
                CostCenters.local.label("centro_custo"),
                CostCenters.departamento.label("departamento"),
                Users.nome.label("supervisor"),
            )
        )
        base_query = apply_cost_center_scope(
            base_query,
            Employees.centro_id,
            token_data,
        )
        # Mantém uma fotografia completa do escopo para não projetar uma
        # avaliação futura que já existe, mas os filtros do painel partem do
        # mesmo recorte que alimenta a tabela e os indicadores.
        option_rows = base_query.all()
        query = base_query

        if filters["start"]:
            query = query.filter(
                ExperienceEvaluation.data_fim_experiencia >= filters["start"]
            )
        if filters["end"]:
            query = query.filter(
                ExperienceEvaluation.data_fim_experiencia <= filters["end"]
            )
        if filters["departments"]:
            query = query.filter(
                CostCenters.departamento.in_(filters["departments"])
            )
        if filters["cost_centers"]:
            query = query.filter(Employees.centro_id.in_(filters["cost_centers"]))
        if filters["supervisors"]:
            query = query.filter(
                ExperienceEvaluation.supervisor_usuario_id.in_(filters["supervisors"])
            )
        if filters["statuses"]:
            query = query.filter(ExperienceEvaluation.status.in_(filters["statuses"]))

        rows = query.order_by(
            ExperienceEvaluation.prazo_supervisor_em.asc(),
            ExperienceEvaluation.id.asc(),
        ).all()
        options = self._filter_options(rows)
        evaluations = [row.ExperienceEvaluation for row in rows]
        status_counts = Counter(evaluation.status for evaluation in evaluations)

        today = date.today()
        employee_query = (
            Employees.query
            .outerjoin(CostCenters, CostCenters.id == Employees.centro_id)
            .outerjoin(Users, Users.id == CostCenters.supervisor_usuario_id)
            .with_entities(
                Employees.nome.label("colaborador"),
                Employees.id.label("colaborador_id"),
                Employees.matricula.label("matricula"),
                Employees.data_admissao.label("data_admissao"),
                CostCenters.local.label("centro_custo"),
                CostCenters.departamento.label("departamento"),
                Users.nome.label("supervisor"),
            )
            .filter(
                Employees.situacao == 1,
                Employees.data_admissao >= today - timedelta(days=89),
                Employees.data_admissao < today + timedelta(days=1),
            )
        )
        if filters["departments"]:
            employee_query = employee_query.filter(
                CostCenters.departamento.in_(filters["departments"])
            )
        if filters["cost_centers"]:
            employee_query = employee_query.filter(
                Employees.centro_id.in_(filters["cost_centers"])
            )
        if filters["supervisors"]:
            employee_query = employee_query.filter(
                CostCenters.supervisor_usuario_id.in_(filters["supervisors"])
            )
        employee_query = apply_cost_center_scope(
            employee_query,
            Employees.centro_id,
            token_data,
        )
        employees_in_experience_rows = employee_query.order_by(
            Employees.data_admissao.asc(),
            Employees.nome.asc(),
        ).all()
        employees_in_experience = len(employees_in_experience_rows)
        employees_in_experience_list = [
            {
                "colaborador": row.colaborador or "Sem identificação",
                "matricula": str(row.matricula) if row.matricula else "—",
                "centro_custo": row.centro_custo or "Sem contrato",
                "departamento": (
                    str(row.departamento)
                    if row.departamento is not None else "—"
                ),
                "supervisor": row.supervisor or "Sem supervisor",
                "admissao": row.data_admissao.isoformat(),
                "fim_experiencia": (
                    row.data_admissao + timedelta(days=89)
                ).isoformat(),
            }
            for row in employees_in_experience_rows[:25]
        ]

        monthly = {
            key: {
                "mes": key,
                "total": 0,
                "concluidas": 0,
                "atrasadas": 0,
                "futuras": 0,
            }
            for key in _month_keys(
                filters["start"] or today.replace(month=1, day=1),
                filters["end"] or today.replace(month=12, day=31),
            )
        }
        existing_evaluations = {
            (
                row.ExperienceEvaluation.colaborador_id,
                row.ExperienceEvaluation.data_fim_experiencia,
            )
            for row in option_rows
        }

        # Projeta apenas tarefas que ainda não foram abertas, sem duplicar a fila atual.
        for employee in employees_in_experience_rows:
            end_date = employee.data_admissao + timedelta(days=89)
            month = end_date.strftime("%Y-%m")
            evaluation_key = (employee.colaborador_id, end_date)
            if month in monthly and evaluation_key not in existing_evaluations:
                monthly[month]["futuras"] += 1

        supervisor_counts = defaultdict(
            lambda: {"total": 0, "pendentes": 0, "atrasadas": 0}
        )
        decisions = Counter()
        priorities = []

        for row in rows:
            evaluation = row.ExperienceEvaluation
            month = evaluation.data_fim_experiencia.strftime("%Y-%m")
            if month in monthly:
                monthly[month]["total"] += 1
                monthly[month]["concluidas"] += int(evaluation.status == "concluida")
                monthly[month]["atrasadas"] += int(evaluation.status == "atrasada")

            supervisor_name = row.supervisor or "Sem supervisor"
            supervisor = supervisor_counts[supervisor_name]
            supervisor["total"] += 1
            supervisor["pendentes"] += int(evaluation.status in OPEN_STATUSES)
            supervisor["atrasadas"] += int(evaluation.status == "atrasada")

            decision = evaluation.decisao_rh or evaluation.decisao_supervisor
            if decision in DECISION_LABELS:
                decisions[decision] += 1

            if evaluation.status in OPEN_STATUSES | {"aguardando_rh"}:
                priorities.append({
                    "id": evaluation.id,
                    "colaborador": row.colaborador_nome or "Sem identificação",
                    "matricula": str(row.matricula) if row.matricula else "—",
                    "centro_custo": row.centro_custo or "Sem contrato",
                    "departamento": str(row.departamento) if row.departamento is not None else "—",
                    "supervisor": supervisor_name,
                    "situacao": evaluation.status,
                    "fim_experiencia": evaluation.data_fim_experiencia.isoformat(),
                    "prazo_supervisor": (
                        evaluation.prazo_supervisor_em.isoformat()
                        if evaluation.prazo_supervisor_em else None
                    ),
                })

        supervisor_list = [
            {"supervisor": name, **values}
            for name, values in supervisor_counts.items()
        ]
        supervisor_list.sort(
            key=lambda item: (-item["atrasadas"], -item["pendentes"], item["supervisor"].casefold())
        )

        return jsonify({
            "periodo": {
                "inicio": filters["start"].isoformat() if filters["start"] else None,
                "fim": filters["end"].isoformat() if filters["end"] else None,
            },
            "indicadores": {
                "em_experiencia": employees_in_experience,
                "avaliacoes": len(evaluations),
                "abertas": status_counts["aberta"] + status_counts["em_preenchimento"],
                "aguardando_rh": status_counts["aguardando_rh"],
                "atrasadas": status_counts["atrasada"],
                "concluidas": status_counts["concluida"],
            },
            "mensal": list(monthly.values()),
            "situacoes": [
                {"situacao": status, "label": label, "total": status_counts[status]}
                for status, label in STATUS_LABELS.items()
                if status_counts[status]
            ],
            "decisoes": [
                {"decisao": decision, "label": label, "total": decisions[decision]}
                for decision, label in DECISION_LABELS.items()
            ],
            "supervisores": supervisor_list[:10],
            "prioridades": priorities[:12],
            "colaboradores_em_experiencia": employees_in_experience_list,
            "filtros": options,
        }), 200
