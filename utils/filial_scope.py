import json
from flask import g, has_request_context, request
from models.centros_de_custo import CostCenters
from models.filiais import Branch, filial_centros_custo, filial_departamentos, filial_usuarios
from models.usuarios import Users
from utils.db import db


def _get_user(token_data):
    user_id = (token_data or {}).get("id")
    return db.session.get(Users, user_id) if user_id else None


def is_admin(token_data):
    """Confere a role atual no banco; o token sozinho não libera escopo global."""
    user = _get_user(token_data)
    return bool(user and str(user.role or "").upper() == "ADMIN")


MATRIX_BRANCH_ID = 1


def is_matrix_user(token_data):
    """Usuário vinculado à filial matriz, cujo ID fixo é 1."""
    user = _get_user(token_data)
    return bool(
        user
        and any(
            branch.ativa and branch.id == MATRIX_BRANCH_ID
            for branch in user.filiais
        )
    )


def can_select_branches(token_data):
    return is_admin(token_data) or is_matrix_user(token_data)


def _requested_branch_ids():
    raw_value = request.headers.get("X-Filial-Ids")

    if raw_value is None:
        return None

    try:
        values = json.loads(raw_value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return set()

    if not isinstance(values, list):
        return set()

    try:
        return {int(value) for value in values}
    except (TypeError, ValueError):
        return set()


def _cost_center_ids_for_branches(branch_ids):
    if not branch_ids:
        return set()

    valid_branch_ids = {
        row[0]
        for row in (
            db.session.query(Branch.id)
            .filter(
                Branch.id.in_(branch_ids),
                Branch.ativa.is_(True),
            )
            .all()
        )
    }

    if valid_branch_ids != set(branch_ids):
        return set()

    direct_rows = (
        db.session.query(filial_centros_custo.c.centro_custo_id)
        .filter(filial_centros_custo.c.filial_id.in_(valid_branch_ids))
        .distinct()
        .all()
    )

    department_rows = (
        db.session.query(CostCenters.id)
        .join(
            filial_departamentos,
            filial_departamentos.c.departamento == CostCenters.departamento,
        )
        .filter(filial_departamentos.c.filial_id.in_(valid_branch_ids))
        .distinct()
        .all()
    )

    return {row[0] for row in [*direct_rows, *department_rows]}


def allowed_cost_center_ids(token_data):
    """
    Retorna:
    - None: acesso global sem filtro;
    - set[int]: centros de custo permitidos;
    - set(): nenhum acesso.
    """
    user = _get_user(token_data)

    if not user:
        return set()

    selectable = can_select_branches(token_data)
    requested_ids = _requested_branch_ids() if has_request_context() else None

    if selectable:
        if requested_ids is None:
            return None
        return _cost_center_ids_for_branches(requested_ids)

    user_id = user.id
    request_cache = getattr(g, "_filial_scope_cache", {}) if has_request_context() else {}

    if user_id in request_cache:
        return request_cache[user_id]

    direct_rows = (
        db.session.query(filial_centros_custo.c.centro_custo_id)
        .join(Branch, Branch.id == filial_centros_custo.c.filial_id)
        .join(filial_usuarios, filial_usuarios.c.filial_id == Branch.id)
        .filter(
            filial_usuarios.c.usuario_id == user_id,
            Branch.ativa.is_(True),
        )
        .distinct()
        .all()
    )

    department_rows = (
        db.session.query(CostCenters.id)
        .join(
            filial_departamentos,
            filial_departamentos.c.departamento == CostCenters.departamento,
        )
        .join(Branch, Branch.id == filial_departamentos.c.filial_id)
        .join(filial_usuarios, filial_usuarios.c.filial_id == Branch.id)
        .filter(
            filial_usuarios.c.usuario_id == user_id,
            Branch.ativa.is_(True),
        )
        .distinct()
        .all()
    )

    allowed_ids = {row[0] for row in [*direct_rows, *department_rows]}

    if has_request_context():
        request_cache[user_id] = allowed_ids
        g._filial_scope_cache = request_cache

    return allowed_ids


def apply_cost_center_scope(query, column, token_data):
    ids = allowed_cost_center_ids(token_data)
    return query if ids is None else query.filter(column.in_(ids))


def can_access_cost_center(token_data, center_id):
    ids = allowed_cost_center_ids(token_data)

    if ids is None:
        return True

    try:
        return int(center_id) in ids
    except (TypeError, ValueError):
        return False


def can_access_supervisor(token_data, supervisor_id):
    ids = allowed_cost_center_ids(token_data)

    if ids is None:
        return True

    if not supervisor_id or not ids:
        return False

    try:
        supervisor_id = int(supervisor_id)
    except (TypeError, ValueError):
        return False

    return (
        db.session.query(CostCenters.id)
        .filter(
            CostCenters.id.in_(ids),
            CostCenters.supervisor_id == supervisor_id,
        )
        .first()
        is not None
    )
