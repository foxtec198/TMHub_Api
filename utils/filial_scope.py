from models.centros_de_custo import CostCenters
from models.filiais import Branch, filial_centros_custo, filial_departamentos, filial_usuarios
from utils.db import db


def is_admin(token_data):
    return str((token_data or {}).get("perm", "")).upper() == "ADMIN"


def allowed_cost_center_ids(token_data):
    """Return None for unrestricted admins and a set for every other user."""
    if is_admin(token_data):
        return None
    user_id = (token_data or {}).get("id")
    if not user_id:
        return set()
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
    return {row[0] for row in [*direct_rows, *department_rows]}


def apply_cost_center_scope(query, column, token_data):
    ids = allowed_cost_center_ids(token_data)
    return query if ids is None else query.filter(column.in_(ids))


def can_access_cost_center(token_data, center_id):
    ids = allowed_cost_center_ids(token_data)
    return ids is None or center_id in ids
