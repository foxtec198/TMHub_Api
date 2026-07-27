from flask import g, has_request_context

from models.centros_de_custo import CostCenters
from models.filiais import Branch, filial_centros_custo, filial_departamentos, filial_usuarios
from models.usuarios import Users
from utils.db import db


def is_admin(token_data):
    """Confere a role atual no banco; o token sozinho nao libera escopo global."""
    user_id = (token_data or {}).get("id")
    if not user_id:
        return False
    user = db.session.get(Users, user_id)
    return bool(user and str(user.role or "").upper() == "ADMIN")


def allowed_cost_center_ids(token_data):
    """Return None for unrestricted admins and a set for every other user."""
    if is_admin(token_data):
        return None
    user_id = (token_data or {}).get("id")
    if not user_id:
        return set()
    request_cache = getattr(g, "_filial_scope_cache", {}) if has_request_context() else {}
    if user_id in request_cache:
        return request_cache[user_id]
    direct_rows = (
        db.session.query(filial_centros_custo.c.centro_custo_id)
        .join(Branch, Branch.id == filial_centros_custo.c.filial_id)
        .join(filial_usuarios, filial_usuarios.c.filial_id == Branch.id)
        .filter(filial_usuarios.c.usuario_id == user_id, Branch.ativa.is_(True))
        .distinct()
        .all()
    )
    department_rows = (
        db.session.query(CostCenters.id)
        .join(filial_departamentos, filial_departamentos.c.departamento == CostCenters.departamento)
        .join(Branch, Branch.id == filial_departamentos.c.filial_id)
        .join(filial_usuarios, filial_usuarios.c.filial_id == Branch.id)
        .filter(filial_usuarios.c.usuario_id == user_id, Branch.ativa.is_(True))
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
    return db.session.query(CostCenters.id).filter(
        CostCenters.id.in_(ids),
        CostCenters.supervisor_id == supervisor_id,
    ).first() is not None
