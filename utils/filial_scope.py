# Utilitários de escopo de filiais.
# Biblioteca padrão.
import json
# Dependências externas.
from flask import g, has_request_context, request
from sqlalchemy import func, or_
# Módulos internos da aplicação.
from models.centros_de_custo import CostCenters, DepartmentConfiguration
from models.filiais import Branch, filial_centros_custo, filial_departamentos, filial_usuarios
from models.usuarios import Users
from utils.db import db


def _get_user(token_data):
    user_id = (token_data or {}).get("id")
    return db.session.get(Users, user_id) if user_id else None


def active_cost_center_ids_query():
    """Centros de departamentos ativos ou ainda sem configuração explícita."""
    return (
        db.session.query(CostCenters.id)
        .outerjoin(
            DepartmentConfiguration,
            DepartmentConfiguration.departamento == CostCenters.departamento,
        )
        .filter(
            or_(
                DepartmentConfiguration.departamento.is_(None),
                DepartmentConfiguration.ativo.is_(True),
            )
        )
    )


def apply_active_department_scope(query, center_column):
    """Oculta departamentos inativos independentemente da filial ou da role."""
    return query.filter(center_column.in_(active_cost_center_ids_query()))


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


def requested_branch_ids():
    """Return the branch ids selected in the MainLayout global selector."""
    return _requested_branch_ids()


def requested_company_ids():
    raw_value = request.headers.get("X-Empresa-Ids") if has_request_context() else None
    if raw_value is None:
        return None
    try:
        values = json.loads(raw_value)
        return {int(value) for value in values} if isinstance(values, list) else set()
    except (TypeError, ValueError, json.JSONDecodeError):
        return set()


def _requested_integer_ids(header_name):
    raw_value = request.headers.get(header_name) if has_request_context() else None
    if raw_value is None:
        return None
    try:
        values = json.loads(raw_value)
        return {int(value) for value in values} if isinstance(values, list) else set()
    except (TypeError, ValueError, json.JSONDecodeError):
        return set()


def requested_department_ids():
    return _requested_integer_ids("X-Departamento-Ids")


def requested_cost_center_ids():
    return _requested_integer_ids("X-Centro-Custo-Ids")


def _apply_company_scope(center_ids):
    company_ids = requested_company_ids()
    if company_ids is None:
        return center_ids
    query = db.session.query(CostCenters.id).filter(CostCenters.empresa_id.in_(company_ids))
    if center_ids is not None:
        query = query.filter(CostCenters.id.in_(center_ids))
    return {row[0] for row in query.all()}


def _apply_structural_scope(center_ids):
    department_ids = requested_department_ids()
    requested_center_ids = requested_cost_center_ids()
    if department_ids is None and requested_center_ids is None:
        return center_ids

    query = db.session.query(CostCenters.id)
    if center_ids is not None:
        query = query.filter(CostCenters.id.in_(center_ids))

    structural_filters = []
    if department_ids is not None:
        structural_filters.append(CostCenters.departamento.in_(department_ids))
    if requested_center_ids is not None:
        structural_filters.append(CostCenters.id.in_(requested_center_ids))

    # Departamentos completos e contratos individuais formam um único recorte
    # aditivo. Ex.: DPTO. 87 + contrato X do DPTO. 301.
    query = query.filter(or_(*structural_filters))
    return {row[0] for row in query.all()}


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
        db.session.query(
            filial_centros_custo.c.filial_id,
            filial_centros_custo.c.centro_custo_id,
        )
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
        if valid_branch_ids
        else []
    )

    # A filial pode combinar departamentos completos com contratos adicionais
    # de outros departamentos. Portanto, os dois vínculos são uma união; a
    # existência de um contrato direto nunca deve anular os departamentos.
    return {row[1] for row in direct_rows} | {row[0] for row in department_rows}


def allowed_cost_center_ids(token_data, include_company=True):
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
            scoped_ids = _apply_company_scope(None) if include_company else None
            return _apply_structural_scope(scoped_ids)
        scoped_ids = _cost_center_ids_for_branches(requested_ids)
        scoped_ids = _apply_company_scope(scoped_ids) if include_company else scoped_ids
        return _apply_structural_scope(scoped_ids)

    user_id = user.id
    request_cache = getattr(g, "_filial_scope_cache", {}) if has_request_context() else {}

    cache_key = (
        user_id,
        tuple(sorted(requested_company_ids() or [])) if include_company else None,
        tuple(sorted(requested_department_ids() or [])),
        tuple(sorted(requested_cost_center_ids() or [])),
    )
    if cache_key in request_cache:
        return request_cache[cache_key]

    user_branch_ids = {
        row[0]
        for row in db.session.query(filial_usuarios.c.filial_id)
        .join(Branch, Branch.id == filial_usuarios.c.filial_id)
        .filter(filial_usuarios.c.usuario_id == user_id, Branch.ativa.is_(True))
        .all()
    }
    allowed_ids = _cost_center_ids_for_branches(user_branch_ids)
    if include_company:
        allowed_ids = _apply_company_scope(allowed_ids)
    allowed_ids = _apply_structural_scope(allowed_ids)

    if has_request_context():
        request_cache[cache_key] = allowed_ids
        g._filial_scope_cache = request_cache

    return allowed_ids


def apply_cost_center_scope(query, column, token_data):
    query = apply_active_department_scope(query, column)
    ids = allowed_cost_center_ids(token_data)
    return query if ids is None else query.filter(column.in_(ids))


def can_access_cost_center(token_data, center_id):
    try:
        normalized_center_id = int(center_id)
    except (TypeError, ValueError):
        return False

    if not active_cost_center_ids_query().filter(
        CostCenters.id == normalized_center_id
    ).first():
        return False

    ids = allowed_cost_center_ids(token_data)

    if ids is None:
        return True

    return normalized_center_id in ids


def can_access_supervisor(token_data, supervisor_id):
    """Compatibilidade de leitura para o cadastro legado de supervisores."""
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


def supervisor_users_query(token_data, center_id=None):
    """Retorna apenas usuários supervisores visíveis no escopo atual.

    O antigo cadastro ``supervisores`` não participa de novos vínculos. A
    filial é validada pelo relacionamento de usuários com filiais para que um
    administrador não consiga direcionar uma operação a um supervisor de
    outra unidade.
    """
    query = Users.query.filter(func.upper(func.trim(Users.role)) == "SUPERVISOR")
    required_branch_ids = None
    allowed_ids = allowed_cost_center_ids(token_data)
    if allowed_ids is not None:
        if not allowed_ids:
            return query.filter(db.false())

        required_branch_ids = _branch_ids_for_cost_centers(allowed_ids)
        if not required_branch_ids:
            return query.filter(db.false())

    if center_id is not None:
        center_branch_ids = _branch_ids_for_cost_centers({int(center_id)})
        if not center_branch_ids:
            return query.filter(db.false())
        required_branch_ids = (
            center_branch_ids
            if required_branch_ids is None
            else required_branch_ids.intersection(center_branch_ids)
        )
        if not required_branch_ids:
            return query.filter(db.false())

    if required_branch_ids is not None:
        query = query.filter(Users.id.in_(
            db.session.query(filial_usuarios.c.usuario_id)
            .filter(filial_usuarios.c.filial_id.in_(required_branch_ids))
        ))

    return query


def _branch_ids_for_cost_centers(center_ids):
    if not center_ids:
        return set()

    direct_rows = (
        db.session.query(
            filial_centros_custo.c.filial_id,
            filial_centros_custo.c.centro_custo_id,
        )
        .filter(filial_centros_custo.c.centro_custo_id.in_(center_ids))
        .distinct()
        .all()
    )
    explicitly_linked_center_ids = {row[1] for row in direct_rows}
    legacy_center_ids = set(center_ids) - explicitly_linked_center_ids
    department_rows = (
        db.session.query(filial_departamentos.c.filial_id)
        .join(
            CostCenters,
            CostCenters.departamento == filial_departamentos.c.departamento,
        )
        .filter(CostCenters.id.in_(legacy_center_ids))
        .distinct()
        .all()
        if legacy_center_ids
        else []
    )
    return {row[0] for row in direct_rows} | {row[0] for row in department_rows}


def can_access_supervisor_user(token_data, user_id, center_id=None):
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return False
    return supervisor_users_query(token_data, center_id).filter(Users.id == user_id).first() is not None
