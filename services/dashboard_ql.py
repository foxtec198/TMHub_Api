from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import jsonify, request
from sqlalchemy import and_, func, or_

from models.centros_de_custo import CostCenters, DepartmentConfiguration
from models.colaboradores import Employees
from models.filiais import (
    Branch,
    filial_centros_custo,
    filial_departamentos,
    filial_usuarios,
)
from models.ql_historico import QLDailySnapshot
from utils.db import db
from utils.filial_scope import (
    allowed_cost_center_ids,
    apply_active_department_scope,
    can_select_branches,
    is_admin,
    requested_branch_ids,
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


class QLDashboardService:
    """Dashboard e memória diária do Quadro de Lotação (QL)."""

    @staticmethod
    def _branch_center_map(branch_ids):
        mapping = {branch_id: set() for branch_id in branch_ids}
        if not mapping:
            return mapping

        direct_rows = (
            db.session.query(
                filial_centros_custo.c.filial_id,
                filial_centros_custo.c.centro_custo_id,
            )
            .filter(filial_centros_custo.c.filial_id.in_(mapping))
            .all()
        )
        for branch_id, center_id in direct_rows:
            mapping[branch_id].add(center_id)

        department_rows = (
            db.session.query(filial_departamentos.c.filial_id, CostCenters.id)
            .select_from(filial_departamentos)
            .join(
                CostCenters,
                CostCenters.departamento == filial_departamentos.c.departamento,
            )
            .filter(filial_departamentos.c.filial_id.in_(mapping))
            .all()
        )
        for branch_id, center_id in department_rows:
            mapping[branch_id].add(center_id)
        return mapping

    @staticmethod
    def _department_rows(center_ids):
        if not center_ids:
            return []
        query = (
            db.session.query(
                CostCenters.departamento.label("departamento"),
                DepartmentConfiguration.capacidade_pessoas.label("capacidade_esperada"),
                func.count(func.distinct(CostCenters.id)).label("centros_quantidade"),
                func.count(Employees.id).label("colaboradores_ativos"),
            )
            .outerjoin(
                DepartmentConfiguration,
                DepartmentConfiguration.departamento == CostCenters.departamento,
            )
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
            .group_by(CostCenters.departamento, DepartmentConfiguration.capacidade_pessoas)
            .order_by(CostCenters.departamento)
        )
        query = apply_active_department_scope(query, CostCenters.id)
        return query.all()

    @classmethod
    def capture_daily(cls, reference_date=None):
        """Atualiza somente a fotografia do dia corrente; dias anteriores congelam."""
        day = reference_date or _today()
        branches = Branch.query.filter(Branch.ativa.is_(True)).all()
        branch_map = cls._branch_center_map([branch.id for branch in branches])
        changed = 0

        for branch in branches:
            for row in cls._department_rows(branch_map.get(branch.id, set())):
                snapshot = QLDailySnapshot.query.filter_by(
                    data_referencia=day,
                    filial_id=branch.id,
                    departamento=row.departamento,
                ).first()
                if not snapshot:
                    snapshot = QLDailySnapshot(
                        data_referencia=day,
                        filial_id=branch.id,
                        departamento=row.departamento,
                    )
                    db.session.add(snapshot)
                snapshot.colaboradores_ativos = int(row.colaboradores_ativos or 0)
                snapshot.capacidade_esperada = (
                    int(row.capacidade_esperada)
                    if row.capacidade_esperada is not None
                    else None
                )
                snapshot.centros_quantidade = int(row.centros_quantidade or 0)
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
    def _history(cls, branch_ids, departments):
        start_date = _today() - timedelta(days=HISTORY_DAYS - 1)
        query = QLDailySnapshot.query.filter(
            QLDailySnapshot.filial_id.in_(branch_ids),
            QLDailySnapshot.data_referencia >= start_date,
        )
        if departments:
            query = query.filter(QLDailySnapshot.departamento.in_(departments))

        by_day = defaultdict(lambda: {"ativos": 0, "metas": {}, "departamentos": set()})
        for row in query.order_by(QLDailySnapshot.data_referencia).all():
            day = by_day[row.data_referencia.isoformat()]
            day["ativos"] += int(row.colaboradores_ativos or 0)
            day["departamentos"].add(row.departamento)
            if row.capacidade_esperada is not None:
                day["metas"][row.departamento] = int(row.capacidade_esperada)

        return [
            {
                "data": day,
                "colaboradores_ativos": values["ativos"],
                "capacidade_esperada": sum(values["metas"].values()),
                "departamentos": len(values["departamentos"]),
            }
            for day, values in sorted(by_day.items())
        ]

    @safe_route
    def read(self, token_data):
        if not has_permission(token_data, "dashboard_ql", "view"):
            return jsonify("Você não possui acesso ao Dashboard de QL."), 403

        # Mantém o ponto do dia atualizado; dados de dias anteriores não são
        # recalculados, preservando o histórico real do quadro.
        self.capture_daily()
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
        departments = [
            self._serialize_department(row)
            for row in self._department_rows(center_ids)
            if not selected_departments or row.departamento in selected_departments
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
            "evolucao": self._history([branch.id for branch in branches], selected_departments),
            "filtros": {
                "departamentos": [
                    {"label": f"DPTO. {row['departamento']}", "value": row["departamento"]}
                    for row in departments
                ],
            },
            "filiais": [{"id": branch.id, "nome": branch.nome} for branch in branches],
            "atualizado_em": datetime.now(SAO_PAULO).isoformat(),
        })
