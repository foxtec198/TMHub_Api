# Regras de negócio de dashboard de rescisões.
# Biblioteca padrão.
from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime as dt
from decimal import Decimal

# Dependências externas.
from flask import jsonify, request
from sqlalchemy import String, cast

# Módulos internos da aplicação.
from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from models.filiais import Branch, filial_centros_custo, filial_departamentos
from models.rescisoes import Termination
from models.supervisores import Supervisors
from utils.db import db
from utils.filial_scope import apply_cost_center_scope
from utils.safe_route import safe_route


ZERO = Decimal("0.00")


def _money(value):
    return Decimal(str(value or 0))


def _parse_date(value, field):
    raw = str(value or "").strip()
    try:
        return dt.strptime(raw, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError(f"{field} invalida; use aaaa-mm-dd.") from error


def _default_start(today):
    month_index = today.year * 12 + today.month - 1 - 5
    return date(month_index // 12, month_index % 12 + 1, 1)


def _period():
    today = date.today()
    start = _parse_date(request.args.get("inicio"), "Data inicial") if request.args.get("inicio") else _default_start(today)
    end = _parse_date(request.args.get("fim"), "Data final") if request.args.get("fim") else today
    if start > end:
        raise ValueError("A data inicial nao pode ser posterior a data final.")
    return start, end


def _csv_values(name):
    return [value.strip() for value in str(request.args.get(name) or "").split(",") if value.strip()]


def _month_keys(start, end):
    result = []
    cursor = date(start.year, start.month, 1)
    limit = date(end.year, end.month, 1)
    while cursor <= limit:
        result.append(cursor.strftime("%Y-%m"))
        cursor = date(
            cursor.year + (1 if cursor.month == 12 else 0),
            1 if cursor.month == 12 else cursor.month + 1,
            1,
        )
    return result


def _branch_map(center_ids):
    """Usa o vinculo direto e recorre ao departamento apenas quando necessario."""
    center_ids = {value for value in center_ids if value is not None}
    result = {center_id: [] for center_id in center_ids}
    if not center_ids:
        return result

    direct_rows = (
        db.session.query(
            filial_centros_custo.c.centro_custo_id,
            Branch.id,
            Branch.nome,
        )
        .join(Branch, Branch.id == filial_centros_custo.c.filial_id)
        .filter(
            filial_centros_custo.c.centro_custo_id.in_(center_ids),
            Branch.ativa.is_(True),
        )
        .all()
    )
    for center_id, branch_id, name in direct_rows:
        result[center_id].append({"id": branch_id, "nome": name})

    missing_ids = {center_id for center_id, branches in result.items() if not branches}
    if missing_ids:
        department_rows = (
            db.session.query(CostCenters.id, Branch.id, Branch.nome)
            .join(
                filial_departamentos,
                filial_departamentos.c.departamento == CostCenters.departamento,
            )
            .join(Branch, Branch.id == filial_departamentos.c.filial_id)
            .filter(CostCenters.id.in_(missing_ids), Branch.ativa.is_(True))
            .all()
        )
        for center_id, branch_id, name in department_rows:
            result[center_id].append({"id": branch_id, "nome": name})

    for center_id in result:
        unique = {branch["id"]: branch for branch in result[center_id]}
        result[center_id] = sorted(unique.values(), key=lambda item: item["nome"].casefold())
    return result


def _branch_name(branches):
    return " / ".join(branch["nome"] for branch in branches) if branches else "Sem filial"


def _row_values(row):
    termination = row[0]
    proventos = _money(termination.proventos)
    descontos = _money(termination.descontos)
    liquido = _money(termination.liquido)
    fgts = _money(termination.fgts_rescisorio)
    return proventos, descontos, liquido, fgts, proventos + fgts


class TerminationDashboardService:
    @safe_route
    def read(self, token_data):
        start, end = _period()

        base_query = (
            db.session.query(
                Termination,
                Employees.nome.label("colaborador_nome"),
                Employees.centro_id.label("centro_custo_id"),
                CostCenters.local.label("centro_custo"),
                CostCenters.departamento.label("departamento"),
                Supervisors.nome.label("supervisor_nome"),
            )
            .join(Employees, Employees.matricula == Termination.matricula)
            .outerjoin(CostCenters, CostCenters.id == Employees.centro_id)
            .outerjoin(Supervisors, Supervisors.id == CostCenters.supervisor_id)
            .filter(Termination.data_demissao.between(start, end))
        )
        base_query = apply_cost_center_scope(base_query, Employees.centro_id, token_data)

        # As opcoes partem do periodo e do escopo de filial, antes dos filtros locais.
        option_rows = base_query.all()
        filter_options = {
            "departamentos": sorted({row.departamento for row in option_rows if row.departamento is not None}),
            "motivos": sorted({row[0].motivo_rescisao for row in option_rows if row[0].motivo_rescisao}, key=str.casefold),
            "contratos": sorted({row.centro_custo for row in option_rows if row.centro_custo}, key=str.casefold),
            "supervisores": sorted({row.supervisor_nome for row in option_rows if row.supervisor_nome}, key=str.casefold),
            "avisos": sorted({row[0].aviso for row in option_rows if row[0].aviso}, key=str.casefold),
        }

        query = base_query
        departments = _csv_values("departamento")
        reasons = _csv_values("motivo")
        contracts = _csv_values("contrato")
        supervisors = _csv_values("supervisor")
        notices = _csv_values("aviso")

        if departments:
            query = query.filter(cast(CostCenters.departamento, String).in_(departments))
        if reasons:
            query = query.filter(Termination.motivo_rescisao.in_(reasons))
        if contracts:
            query = query.filter(CostCenters.local.in_(contracts))
        if supervisors:
            query = query.filter(Supervisors.nome.in_(supervisors))
        if notices:
            query = query.filter(Termination.aviso.in_(notices))

        rows = query.order_by(Termination.data_demissao.desc(), Termination.id.desc()).all()
        branches_by_center = _branch_map(row.centro_custo_id for row in rows)

        totals = {
            "total_rescisoes": len(rows),
            "proventos": ZERO,
            "descontos": ZERO,
            "liquido": ZERO,
            "fgts_rescisorio": ZERO,
            "custo_total": ZERO,
        }
        monthly = {
            key: {
                "mes": key,
                "quantidade": 0,
                "proventos": ZERO,
                "descontos": ZERO,
                "liquido": ZERO,
                "fgts_rescisorio": ZERO,
                "custo_total": ZERO,
            }
            for key in _month_keys(start, end)
        }
        reasons_data = defaultdict(lambda: {"quantidade": 0, "custo_total": ZERO})
        branch_data = defaultdict(lambda: {"quantidade": 0, "proventos": ZERO, "descontos": ZERO, "liquido": ZERO, "fgts_rescisorio": ZERO, "custo_total": ZERO})
        contract_data = defaultdict(lambda: {"quantidade": 0, "proventos": ZERO, "descontos": ZERO, "liquido": ZERO, "fgts_rescisorio": ZERO, "custo_total": ZERO})

        recent = []
        for row in rows:
            termination = row[0]
            proventos, descontos, liquido, fgts, cost = _row_values(row)
            branches = branches_by_center.get(row.centro_custo_id, [])
            branch = _branch_name(branches)
            contract = row.centro_custo or "Sem contrato"

            totals["proventos"] += proventos
            totals["descontos"] += descontos
            totals["liquido"] += liquido
            totals["fgts_rescisorio"] += fgts
            totals["custo_total"] += cost

            month = monthly[termination.data_demissao.strftime("%Y-%m")]
            month["quantidade"] += 1
            month["proventos"] += proventos
            month["descontos"] += descontos
            month["liquido"] += liquido
            month["fgts_rescisorio"] += fgts
            month["custo_total"] += cost

            reason = termination.motivo_rescisao or "Nao informado"
            reasons_data[reason]["quantidade"] += 1
            reasons_data[reason]["custo_total"] += cost

            for target in (branch_data[branch], contract_data[row.centro_custo_id or 0]):
                target["quantidade"] += 1
                target["proventos"] += proventos
                target["descontos"] += descontos
                target["liquido"] += liquido
                target["fgts_rescisorio"] += fgts
                target["custo_total"] += cost

            contract_data[row.centro_custo_id or 0].update({
                "centro_custo_id": row.centro_custo_id,
                "contrato": contract,
                "departamento": row.departamento,
                "supervisor": row.supervisor_nome or "Sem supervisor",
                "filial": branch,
            })

            if len(recent) < 15:
                recent.append({
                    "id": termination.id,
                    "matricula": termination.matricula,
                    "nome": row.colaborador_nome,
                    "data_demissao": termination.data_demissao.isoformat(),
                    "motivo": reason,
                    "aviso": termination.aviso,
                    "filial": branch,
                    "contrato": contract,
                    "liquido": float(liquido),
                    "custo_total": float(cost),
                })

        total_count = totals["total_rescisoes"]
        totals["custo_medio"] = totals["custo_total"] / total_count if total_count else ZERO

        monthly_list = []
        for item in monthly.values():
            monthly_list.append({key: float(value) if isinstance(value, Decimal) else value for key, value in item.items()})

        reasons_list = [
            {
                "motivo": reason,
                "quantidade": item["quantidade"],
                "custo_total": float(item["custo_total"]),
                "percentual": round(item["quantidade"] * 100 / total_count, 1) if total_count else 0,
            }
            for reason, item in reasons_data.items()
        ]
        reasons_list.sort(key=lambda item: (-item["quantidade"], item["motivo"].casefold()))

        branches_list = []
        for branch, item in branch_data.items():
            branches_list.append({
                "filial": branch,
                **{key: float(value) if isinstance(value, Decimal) else value for key, value in item.items()},
                "custo_medio": float(item["custo_total"] / item["quantidade"]) if item["quantidade"] else 0,
            })
        branches_list.sort(key=lambda item: (-item["custo_total"], item["filial"].casefold()))

        contracts_list = []
        for item in contract_data.values():
            contracts_list.append({
                **{key: float(value) if isinstance(value, Decimal) else value for key, value in item.items()},
                "custo_medio": float(item["custo_total"] / item["quantidade"]) if item["quantidade"] else 0,
            })
        contracts_list.sort(key=lambda item: (-item["custo_total"], item["contrato"].casefold()))

        return jsonify({
            "periodo": {"inicio": start.isoformat(), "fim": end.isoformat()},
            "indicadores": {key: float(value) if isinstance(value, Decimal) else value for key, value in totals.items()},
            "mensal": monthly_list,
            "motivos": reasons_list,
            "filiais": branches_list,
            "contratos": contracts_list,
            "recentes": recent,
            "filtros": filter_options,
        }), 200
