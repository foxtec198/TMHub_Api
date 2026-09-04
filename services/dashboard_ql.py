from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import jsonify, request
from sqlalchemy import and_, func, or_

from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from models.filiais import (
    Branch,
    filial_centros_custo,
    filial_departamentos,
    filial_usuarios,
)
from models.empresas import Company
from models.ql_historico import QLDailySnapshot, QLDepartmentCapacity
from utils.db import db
from utils.filial_scope import (
    allowed_cost_center_ids,
    can_select_branches,
    requested_branch_ids,
    requested_company_ids,
)
from utils.permissions import has_permission
from utils.safe_route import safe_route


SAO_PAULO = ZoneInfo("America/Sao_Paulo")
WORKING_STATUS_ID = 1
HISTORY_DAYS = 30


def _today():
    return datetime.now(SAO_PAULO).date()


def _selected_values(name):
    return {
        int(value)
        for raw in request.args.getlist(name)
        for value in str(raw).split(",")
        if str(value).strip().isdigit()
    }


def _selected_list(name):
    """Lê parâmetros como lista de valores (não apenas números)."""
    result = set()
    for raw in request.args.getlist(name):
        for value in str(raw).split(","):
            stripped = str(value).strip()
            if stripped:
                result.add(stripped)
    return result


def _selected_company_departments():
    selected = set()
    for raw in request.args.getlist("departamento_empresa"):
        for value in str(raw).split(","):
            company_id, separator, department = value.partition(":")
            if separator and company_id.isdigit() and department.isdigit():
                selected.add((int(company_id), int(department)))
    return selected


class QLDashboardService:
    """Dashboard e memória diária do Quadro de Lotação (QL)."""

    @staticmethod
    def _branch_center_map(branch_ids):
        mapping = {branch_id: set() for branch_id in branch_ids}
        if not mapping:
            return mapping

        # Centros de custo diretamente vinculados à filial
        direct_rows = (
            db.session.query(
                filial_centros_custo.c.filial_id,
                filial_centros_custo.c.centro_custo_id,
            )
            .filter(filial_centros_custo.c.filial_id.in_(mapping))
            .distinct()
            .all()
        )
        for branch_id, center_id in direct_rows:
            mapping[branch_id].add(center_id)

        # Departamentos diretamente vinculados à filial
        department_rows = (
            db.session.query(
                filial_departamentos.c.filial_id,
                CostCenters.id.label("centro_custo_id"),
            )
            .join(
                CostCenters,
                CostCenters.departamento == filial_departamentos.c.departamento,
            )
            .filter(filial_departamentos.c.filial_id.in_(mapping))
            .distinct()
            .all()
        )
        for branch_id, center_id in department_rows:
            mapping[branch_id].add(center_id)

        # O vínculo direto é a fonte oficial: o mesmo DPTO pode existir em
        # empresas e filiais diferentes, portanto o número isolado é ambíguo.
        return mapping

    @staticmethod
    def _department_rows(center_ids):
        if not center_ids:
            return []
        query = (
            db.session.query(
                CostCenters.departamento.label("departamento"),
                CostCenters.empresa_id.label("empresa_id"),
                Company.nome.label("empresa_nome"),
                QLDepartmentCapacity.capacidade_esperada.label("capacidade_esperada"),
                func.count(func.distinct(CostCenters.id)).label("centros_quantidade"),
                func.count(Employees.id).label("colaboradores_ativos"),
            )
            .outerjoin(
                QLDepartmentCapacity,
                and_(
                    QLDepartmentCapacity.empresa_id == CostCenters.empresa_id,
                    QLDepartmentCapacity.departamento == CostCenters.departamento,
                ),
            )
            .join(Company, Company.id == CostCenters.empresa_id)
            .outerjoin(
                Employees,
                and_(
                    Employees.centro_id == CostCenters.id,
                    Employees.situacao == WORKING_STATUS_ID,
                ),
            )
            .filter(
                CostCenters.id.in_(center_ids),
                CostCenters.departamento.isnot(None),
            )
            .group_by(
                CostCenters.empresa_id,
                Company.nome,
                CostCenters.departamento,
                QLDepartmentCapacity.capacidade_esperada,
            )
            .order_by(Company.nome, CostCenters.departamento)
        )
        return query.all()

    @classmethod
    def capture_daily(cls, reference_date=None):
        """Atualiza somente a fotografia do dia corrente; dias anteriores congelam."""
        day = reference_date or _today()
        branches = Branch.query.filter(Branch.ativa.is_(True)).all()
        if not branches:
            return 0

        branch_map = cls._branch_center_map([branch.id for branch in branches])
        existing_snapshots = {
            (snapshot.filial_id, snapshot.empresa_id, snapshot.departamento): snapshot
            for snapshot in QLDailySnapshot.query.filter(
                QLDailySnapshot.data_referencia == day,
                QLDailySnapshot.filial_id.in_([branch.id for branch in branches]),
            ).all()
        }
        changed = 0

        for branch in branches:
            for row in cls._department_rows(branch_map.get(branch.id, set())):
                snapshot = existing_snapshots.get((branch.id, row.empresa_id, row.departamento))
                if not snapshot:
                    snapshot = QLDailySnapshot(
                        data_referencia=day,
                        filial_id=branch.id,
                        empresa_id=row.empresa_id,
                        departamento=row.departamento,
                    )
                    db.session.add(snapshot)
                    existing_snapshots[(branch.id, row.empresa_id, row.departamento)] = snapshot

                ativos = int(row.colaboradores_ativos or 0)
                meta = (
                    int(row.capacidade_esperada)
                    if row.capacidade_esperada is not None
                    else None
                )
                centros = int(row.centros_quantidade or 0)
                if (
                    snapshot.colaboradores_ativos != ativos
                    or snapshot.capacidade_esperada != meta
                    or snapshot.centros_quantidade != centros
                ):
                    snapshot.colaboradores_ativos = ativos
                    snapshot.capacidade_esperada = meta
                    snapshot.centros_quantidade = centros
                    changed += 1

        if changed:
            db.session.commit()
        return changed

    @staticmethod
    def _visible_branches(token_data):
        query = Branch.query.filter(Branch.ativa.is_(True))
        if not can_select_branches(token_data):
            query = query.join(
                filial_usuarios,
                filial_usuarios.c.filial_id == Branch.id,
            ).filter(filial_usuarios.c.usuario_id == token_data.get("id"))
        branches = query.distinct().order_by(Branch.nome).all()
        available_ids = {branch.id for branch in branches}
        requested_ids = requested_branch_ids()
        if requested_ids is not None:
            if not requested_ids.issubset(available_ids):
                return [], "Você não possui acesso a uma ou mais filiais selecionadas."
            branches = [branch for branch in branches if branch.id in requested_ids]
        return branches, None

    @staticmethod
    def _serialize_department(row):
        active = int(row.colaboradores_ativos or 0)
        expected = (
            int(row.capacidade_esperada)
            if row.capacidade_esperada is not None
            else None
        )
        difference = active - expected if expected is not None else None
        return {
            "departamento": row.departamento,
            "empresa_id": row.empresa_id,
            "empresa_nome": row.empresa_nome,
            "colaboradores_ativos": active,
            "capacidade_esperada": expected,
            "centros_quantidade": int(row.centros_quantidade or 0),
            "saldo": difference,
            "situacao": (
                "SEM_META"
                if expected is None
                else "DEFICIT"
                if difference < 0
                else "COMPLETO"
                if difference == 0
                else "ACIMA"
            ),
        }

    @classmethod
    def _history(cls, branch_ids, company_ids, departments, company_departments=None):
        start_date = _today() - timedelta(days=HISTORY_DAYS - 1)
        query = QLDailySnapshot.query.filter(
            QLDailySnapshot.filial_id.in_(branch_ids),
            QLDailySnapshot.data_referencia >= start_date,
        )
        if company_ids is not None:
            query = query.filter(QLDailySnapshot.empresa_id.in_(company_ids))
        if departments:
            query = query.filter(QLDailySnapshot.departamento.in_(departments))

        by_day = defaultdict(lambda: {"ativos": 0, "metas": {}, "departamentos": set()})
        for row in query.order_by(QLDailySnapshot.data_referencia).all():
            if company_departments and (row.empresa_id, row.departamento) not in company_departments:
                continue
            day = by_day[row.data_referencia.isoformat()]
            day["ativos"] += int(row.colaboradores_ativos or 0)
            identity = (row.empresa_id, row.departamento)
            day["departamentos"].add(identity)
            if row.capacidade_esperada is not None:
                day["metas"][identity] = int(row.capacidade_esperada)

        return [
            {
                "data": day,
                "colaboradores_ativos": values["ativos"],
                "capacidade_esperada": sum(values["metas"].values()),
                "departamentos": len(values["departamentos"]),
            }
            for day, values in sorted(by_day.items())
        ]

    @classmethod
    def _resolve_reference_month(cls, raw_value):
        today = _today()
        if not raw_value:
            return today.replace(day=1), None
        text = str(raw_value).strip()
        for fmt in ("%Y-%m", "%m/%Y", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(text, fmt).date()
                return parsed.replace(day=1), None
            except ValueError:
                continue
        return today.replace(day=1), "Mês inválido. Use o formato AAAA-MM."

    @staticmethod
    def _month_days(reference):
        if reference.month == 12:
            next_month = reference.replace(year=reference.year + 1, month=1)
        else:
            next_month = reference.replace(month=reference.month + 1)
        return [
            reference + timedelta(days=offset)
            for offset in range((next_month - reference).days)
        ]

    @staticmethod
    def _situacao_dia(ativos, meta):
        if meta is None:
            return "SEM_META"
        if ativos < meta:
            return "DEFICIT"
        if ativos == meta:
            return "COMPLETO"
        return "ACIMA"

    @classmethod
    def _build_daily_payload(cls, departments, month_days, snapshot_lookup):
        rows = []
        for department in departments:
            daily = []
            for day in month_days:
                key = day.isoformat()
                snapshot = snapshot_lookup.get((key, department["empresa_id"], department["departamento"]))
                ativos = int(snapshot["ativos"]) if snapshot else None
                meta = (
                    int(snapshot["meta"])
                    if snapshot and snapshot["meta"] is not None
                    else department["capacidade_esperada"]
                )
                if meta is not None:
                    meta = int(meta)
                daily.append({
                    "data": key,
                    "colaboradores_ativos": ativos,
                    "capacidade_esperada": meta,
                    "saldo": (ativos - meta) if ativos is not None and meta is not None else None,
                    "situacao": (
                        cls._situacao_dia(ativos, meta)
                        if ativos is not None
                        else "SEM_DADOS"
                    ),
                })

            days_with_data = [day for day in daily if day["colaboradores_ativos"] is not None]
            days_with_target = [
                day
                for day in days_with_data
                if day["capacidade_esperada"] is not None
            ]
            media_real = (
                round(
                    sum(day["colaboradores_ativos"] for day in days_with_data)
                    / len(days_with_data),
                    2,
                )
                if days_with_data
                else None
            )
            media_meta = (
                round(
                    sum(day["capacidade_esperada"] for day in days_with_target)
                    / len(days_with_target),
                    2,
                )
                if days_with_target
                else None
            )
            total_real = sum(day["colaboradores_ativos"] for day in days_with_target)
            total_meta = sum(day["capacidade_esperada"] for day in days_with_target)
            if not days_with_data:
                percentual = None
                situacao_mes = "SEM_DADOS"
            elif not days_with_target:
                percentual = None
                situacao_mes = "SEM_META"
            elif total_meta <= 0:
                # Meta zero não representa divisão impossível: qualquer
                # efetivo atende o quadro, seguindo a situação já calculada.
                percentual = 100
                situacao_mes = cls._situacao_dia(total_real, total_meta)
            else:
                percentual = round((total_real / total_meta) * 100, 2)
                situacao_mes = cls._situacao_dia(total_real, total_meta)

            rows.append({
                "departamento": department["departamento"],
                "empresa_id": department["empresa_id"],
                "empresa_nome": department["empresa_nome"],
                "dias": daily,
                "media_real": media_real,
                "media_meta": media_meta,
                "percentual": percentual,
                "situacao_mes": situacao_mes,
            })
        return rows

    @safe_route
    def read_diario(self, token_data):
        if not has_permission(token_data, "dashboard_ql", "view"):
            return jsonify("Você não possui acesso ao Dashboard de QL."), 403

        branches, error = self._visible_branches(token_data)
        if error:
            return jsonify(error), 403
        if not branches:
            return jsonify({"mes": None, "dias": [], "departamentos": [], "filtros": {"departamentos": []}})

        reference_month, parse_error = self._resolve_reference_month(request.args.get("mes"))
        if parse_error:
            return jsonify(parse_error), 400

        allowed_centers = allowed_cost_center_ids(token_data)
        branch_centers = self._branch_center_map([branch.id for branch in branches])
        center_ids = set().union(*branch_centers.values())
        if allowed_centers is not None:
            center_ids.intersection_update(allowed_centers)

        selected_departments = _selected_values("departamento")
        selected_companies = _selected_values("empresa")
        selected_situacoes = _selected_list("situacao")
        global_company_ids = requested_company_ids()
        if global_company_ids is not None:
            selected_companies = global_company_ids
        selected_company_departments = _selected_company_departments()
        departments = [
            self._serialize_department(row)
            for row in self._department_rows(center_ids)
            if (not selected_departments or row.departamento in selected_departments)
            and (not selected_companies or row.empresa_id in selected_companies)
            and (not selected_company_departments or (row.empresa_id, row.departamento) in selected_company_departments)
            and (not selected_situacoes or self._serialize_department(row)["situacao"] in selected_situacoes)
        ]

        month_days = self._month_days(reference_month)
        department_filter = [row["departamento"] for row in departments] if departments else [-1]
        snapshots = QLDailySnapshot.query.filter(
            QLDailySnapshot.filial_id.in_([branch.id for branch in branches]),
            QLDailySnapshot.data_referencia >= month_days[0],
            QLDailySnapshot.data_referencia <= month_days[-1],
            QLDailySnapshot.departamento.in_(department_filter),
        ).all()
        if selected_companies:
            snapshots = [row for row in snapshots if row.empresa_id in selected_companies]
        if selected_company_departments:
            snapshots = [row for row in snapshots if (row.empresa_id, row.departamento) in selected_company_departments]

        lookup = {}
        for row in snapshots:
            key = (row.data_referencia.isoformat(), row.empresa_id, row.departamento)
            values = lookup.setdefault(key, {"ativos": 0, "meta": None})
            values["ativos"] += int(row.colaboradores_ativos or 0)
            if row.capacidade_esperada is not None:
                # A meta é configurada por departamento; em uma seleção de
                # filiais ela não deve ser somada uma vez por filial.
                values["meta"] = max(values["meta"] or 0, int(row.capacidade_esperada))

        return jsonify({
            "mes": reference_month.strftime("%Y-%m"),
            "dias": [day.isoformat() for day in month_days],
            "departamentos": self._build_daily_payload(departments, month_days, lookup),
            "filtros": {
                "departamentos": [
                    {"label": f"{row['empresa_nome']} · DPTO. {row['departamento']}", "value": f"{row['empresa_id']}:{row['departamento']}"}
                    for row in departments
                ],
                "empresas": sorted(
                    {row["empresa_id"]: {"label": row["empresa_nome"], "value": row["empresa_id"]} for row in departments}.values(),
                    key=lambda item: item["label"],
                ),
            },
            "atualizado_em": datetime.now(SAO_PAULO).isoformat(),
        })

    @safe_route
    def read(self, token_data):
        if not has_permission(token_data, "dashboard_ql", "view"):
            return jsonify("Você não possui acesso ao Dashboard de QL."), 403

        branches, error = self._visible_branches(token_data)
        if error:
            return jsonify(error), 403
        if not branches:
            return jsonify({"resumo": {}, "departamentos": [], "evolucao": [], "filtros": {"departamentos": []}})

        allowed_centers = allowed_cost_center_ids(token_data)
        branch_centers = self._branch_center_map([branch.id for branch in branches])
        center_ids = set().union(*branch_centers.values())
        if allowed_centers is not None:
            center_ids.intersection_update(allowed_centers)

        selected_departments = _selected_values("departamento")
        selected_companies = _selected_values("empresa")
        selected_situacoes = _selected_list("situacao")
        global_company_ids = requested_company_ids()
        if global_company_ids is not None:
            selected_companies = global_company_ids
        selected_company_departments = _selected_company_departments()
        departments = [
            self._serialize_department(row)
            for row in self._department_rows(center_ids)
            if (not selected_departments or row.departamento in selected_departments)
            and (not selected_companies or row.empresa_id in selected_companies)
            and (not selected_company_departments or (row.empresa_id, row.departamento) in selected_company_departments)
            and (not selected_situacoes or self._serialize_department(row)["situacao"] in selected_situacoes)
        ]
        expected_rows = [row for row in departments if row["capacidade_esperada"] is not None]
        summary = {
            "colaboradores_ativos": sum(row["colaboradores_ativos"] for row in departments),
            "capacidade_esperada": sum(row["capacidade_esperada"] for row in expected_rows),
            "departamentos": len(departments),
            "departamentos_sem_meta": len(departments) - len(expected_rows),
            "deficit": sum(max(0, -int(row["saldo"] or 0)) for row in expected_rows),
            "excedente": sum(max(0, int(row["saldo"] or 0)) for row in expected_rows),
        }
        return jsonify({
            "resumo": summary,
            "departamentos": departments,
            "evolucao": self._history([branch.id for branch in branches], selected_companies, selected_departments, selected_company_departments),
            "filtros": {
                "departamentos": [
                    {"label": f"{row['empresa_nome']} · DPTO. {row['departamento']}", "value": f"{row['empresa_id']}:{row['departamento']}"}
                    for row in departments
                ],
                "empresas": sorted(
                    {row["empresa_id"]: {"label": row["empresa_nome"], "value": row["empresa_id"]} for row in departments}.values(),
                    key=lambda item: item["label"],
                ),
            },
            "filiais": [{"id": branch.id, "nome": branch.nome} for branch in branches],
            "atualizado_em": datetime.now(SAO_PAULO).isoformat(),
        })
