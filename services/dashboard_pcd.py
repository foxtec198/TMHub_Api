from flask import jsonify

from models.centros_de_custo import CostCenters, db
from models.colaboradores import Employees
from models.filiais import Branch,filial_centros_custo,filial_departamentos,filial_usuarios


from utils.filial_scope import (
    allowed_cost_center_ids,
    can_select_branches,
    requested_branch_ids,
)
from utils.safe_route import safe_route


SITUACOES_ATIVAS = {1, 9, 18}
SITUACAO_DEMITIDO = 8
META_PCD = 5


def _empty_pcd_dashboard(branches):
    return {
        "filiais_disponiveis": [
            {"id": branch.id, "nome": branch.nome}
            for branch in branches
        ],
        "resumo": {
            "total_colaboradores": 0,
            "total_pcd": 0,
            "pcd_ativos": 0,
            "pcd_afastados": 0,
            "percentual_pcd": 0,
            "meta_percentual": META_PCD,
        },
        "filiais": [],
        "tipos_deficiencia": [],
    }


class PcdDashboardService:
    @safe_route
    def read(self, token_data):
        branch_query = Branch.query.filter(Branch.ativa.is_(True))
        if not can_select_branches(token_data):
            branch_query = (
                branch_query
                .join(
                    filial_usuarios,
                    filial_usuarios.c.filial_id == Branch.id,
                )
                .filter(
                    filial_usuarios.c.usuario_id == token_data.get("id"),
                )
            )

        available_branches = (
            branch_query
            .distinct()
            .order_by(Branch.nome.asc())
            .all()
        )
        available_ids = {branch.id for branch in available_branches}

        # The MainLayout selector is the sole source of branch filtering.
        global_branch_ids = (
            requested_branch_ids()
            if can_select_branches(token_data)
            else None
        )
        if global_branch_ids is not None and global_branch_ids - available_ids:
            return jsonify("Filiais selecionadas sem permissao."), 403
        requested_ids = (
            available_ids if global_branch_ids is None else global_branch_ids
        )
        if requested_ids is None:
            return jsonify("Informe filiais válidas."), 400
        if requested_ids - available_ids:
            return jsonify("Você não possui acesso a uma ou mais filiais selecionadas."), 403

        selected_ids = requested_ids
        selected_branches = [
            branch
            for branch in available_branches
            if branch.id in selected_ids
        ]
        if not selected_branches:
            return jsonify(_empty_pcd_dashboard(available_branches)), 200

        branch_centers = {
            branch.id: set()
            for branch in selected_branches
        }

        direct_rows = (
            db.session.query(
                filial_centros_custo.c.filial_id,
                filial_centros_custo.c.centro_custo_id,
            )
            .filter(
                filial_centros_custo.c.filial_id.in_(selected_ids),
            )
            .all()
        )
        for branch_id, center_id in direct_rows:
            branch_centers[branch_id].add(center_id)

        department_rows = (
            db.session.query(
                filial_departamentos.c.filial_id,
                CostCenters.id,
            )
            .select_from(filial_departamentos)
            .join(
                CostCenters,
                CostCenters.departamento
                == filial_departamentos.c.departamento,
            )
            .filter(
                filial_departamentos.c.filial_id.in_(selected_ids),
            )
            .all()
        )
        for branch_id, center_id in department_rows:
            branch_centers[branch_id].add(center_id)

        selected_center_ids = set().union(*branch_centers.values())
        scoped_center_ids = allowed_cost_center_ids(token_data)
        if scoped_center_ids is not None:
            selected_center_ids &= scoped_center_ids
        if not selected_center_ids:
            return jsonify(
                _empty_pcd_dashboard(available_branches),
            ), 200

        employees = (
            db.session.query(
                Employees.id,
                Employees.centro_id,
                Employees.situacao,
                Employees.pcd,
                Employees.type_pcd,
            )
            .filter(
                Employees.centro_id.in_(selected_center_ids),
                Employees.situacao.isnot(None),
                Employees.situacao != SITUACAO_DEMITIDO,
            )
            .all()
        )

        total_employees = len(employees)
        pcd_employees = [
            employee
            for employee in employees
            if employee.pcd
        ]
        active_pcd = sum(
            employee.situacao in SITUACOES_ATIVAS
            for employee in pcd_employees
        )
        away_pcd = len(pcd_employees) - active_pcd
        pcd_percentage = (
            round(
                (len(pcd_employees) / total_employees) * 100,
                2,
            )
            if total_employees
            else 0
        )

        branch_data = []
        for branch in selected_branches:
            center_ids = branch_centers[branch.id]
            branch_pcd = [
                employee
                for employee in pcd_employees
                if employee.centro_id in center_ids
            ]
            branch_data.append({
                "id": branch.id,
                "nome": branch.nome,
                "pcd_ativos": sum(
                    employee.situacao in SITUACOES_ATIVAS
                    for employee in branch_pcd
                ),
                "pcd_afastados": sum(
                    employee.situacao not in SITUACOES_ATIVAS
                    for employee in branch_pcd
                ),
            })

        type_counts = {}
        for employee in pcd_employees:
            types = {
                value.strip()
                for value in (employee.type_pcd or "").split(",")
                if value.strip()
            } or {"Não informado"}
            for disability_type in types:
                type_counts[disability_type] = (
                    type_counts.get(disability_type, 0) + 1
                )

        return jsonify({
            "filiais_disponiveis": [
                {"id": branch.id, "nome": branch.nome}
                for branch in available_branches
            ],
            "resumo": {
                "total_colaboradores": total_employees,
                "total_pcd": len(pcd_employees),
                "pcd_ativos": active_pcd,
                "pcd_afastados": away_pcd,
                "percentual_pcd": pcd_percentage,
                "meta_percentual": META_PCD,
            },
            "filiais": branch_data,
            "tipos_deficiencia": [
                {"tipo": disability_type, "total": total}
                for disability_type, total in sorted(
                    type_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
        }), 200
