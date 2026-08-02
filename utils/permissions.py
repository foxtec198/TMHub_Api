from models.permissoes import UserPermission
from models.usuarios import Users
from utils.db import db
from utils.token import decode_token


PERMISSION_CATALOG = [
    {"key": "dashboard_reposicoes", "label": "Dashboard de Reposições", "group": "Dashboards", "actions": ["view"]},
    {"key": "dashboard_reposicoes_ods", "label": "Painel ODS de Reposições", "group": "Dashboards", "actions": ["view"]},
    {"key": "dashboard_colaboradores", "label": "Colaboradores por departamento", "group": "Dashboards", "actions": ["view"]},
    {"key": "dashboard_ponto48", "label": "Ponto 48 horas", "group": "Dashboards", "actions": ["view", "create", "edit"]},
    {"key": "dashboard_admissoes", "label": "Dashboard de Admissões", "group": "Dashboards", "actions": ["view"]},
    {"key": "dashboard_faltas", "label": "Dashboard de Faltas", "group": "Dashboards", "actions": ["view"]},
    {"key": "dashboard_logistica", "label": "Dashboard de Logística", "group": "Dashboards", "actions": ["view"]},
    {"key": "admissoes", "label": "Vagas e admissões", "group": "Operação", "actions": ["view", "create", "edit"]},
    {"key": "controle_faltas", "label": "Controle de Faltas", "group": "Operação", "actions": ["view", "edit"]},
    {"key": "controle_glosas", "label": "Controle de Glosas", "group": "Operação", "actions": ["view", "create", "edit"]},
    {"key": "reposicoes", "label": "Requisições de reposição", "group": "Reposições", "actions": ["view", "create", "edit"]},
    {"key": "historico_reposicoes", "label": "Histórico de reposições", "group": "Reposições", "actions": ["view", "edit"]},
    {"key": "reservas", "label": "Reservas técnicas", "group": "Reposições", "actions": ["view", "create", "edit"]},
    {"key": "estoque_produtos", "label": "Produtos", "group": "Estoque", "actions": ["view", "create", "edit"]},
    {"key": "estoque_codigos", "label": "Códigos de barras", "group": "Estoque", "actions": ["view", "create"]},
    {"key": "estoque_movimentos", "label": "Movimentações", "group": "Estoque", "actions": ["view", "create", "edit"]},
    {"key": "projetos", "label": "Meus Projetos", "group": "Outros", "actions": ["view", "create", "edit"]},
    {"key": "indicador_pcd", "label": "Indicador PCD", "group": "Indicadores", "actions": ["view", "edit"]},
    {"key": "estrutura", "label": "Estrutura", "group": "Operação", "actions": ["view", "create", "edit"]},
    {"key": "schedular", "label": "TM Schedular", "group": "Operação", "actions": ["view", "create", "edit"]},
    {"key": "dashboard_pcd", "label": "Dashboard PCD", "group": "Dashboards", "actions": ["view"]},
]

CATALOG_BY_KEY = {item["key"]: item for item in PERMISSION_CATALOG}
ACTION_COLUMNS = {
    "view": "pode_ver",
    "create": "pode_criar",
    "edit": "pode_alterar",
}
LEGACY_RESTRICTED = {"controle_faltas", "controle_glosas", "dashboard_faltas"}


def _legacy_permission(user, screen, action):
    if screen in LEGACY_RESTRICTED:
        return bool(user.gerencia_faltas)
    return True


def serialize_permissions(user):
    if not user:
        return []
    is_admin = str(user.role or "").upper() == "ADMIN"
    rows = UserPermission.query.filter_by(usuario_id=user.id).all()
    explicit = {row.tela: row for row in rows}
    has_explicit_matrix = bool(rows)
    result = []
    for item in PERMISSION_CATALOG:
        row = explicit.get(item["key"])
        permissions = {}
        for action, column in ACTION_COLUMNS.items():
            if action not in item["actions"]:
                permissions[action] = False
            elif is_admin:
                permissions[action] = True
            elif row:
                permissions[action] = bool(getattr(row, column))
            elif not has_explicit_matrix:
                permissions[action] = _legacy_permission(user, item["key"], action)
            else:
                permissions[action] = False
        result.append({"screen": item["key"], **permissions})
    return result


def has_permission(token_data, screen, action="view"):
    if action not in ACTION_COLUMNS or screen not in CATALOG_BY_KEY:
        return False
    user = db.session.get(Users, (token_data or {}).get("id"))
    if not user:
        return False
    if str(user.role or "").upper() == "ADMIN":
        return True
    permissions = {item["screen"]: item for item in serialize_permissions(user)}
    return bool(permissions.get(screen, {}).get(action))


def replace_permissions(user, payload):
    if payload is None:
        return None
    if not isinstance(payload, list):
        return "Informe uma lista válida de permissões."

    normalized = {}
    for item in payload:
        if not isinstance(item, dict):
            return "Uma ou mais permissões são inválidas."
        screen = str(item.get("screen") or "").strip()
        if screen not in CATALOG_BY_KEY:
            return f"A tela '{screen}' não existe no catálogo de permissões."
        allowed_actions = CATALOG_BY_KEY[screen]["actions"]
        can_view = bool(item.get("view"))
        can_create = bool(item.get("create")) if "create" in allowed_actions else False
        can_edit = bool(item.get("edit")) if "edit" in allowed_actions else False
        if can_create or can_edit:
            can_view = True
        normalized[screen] = (can_view, can_create, can_edit)

    UserPermission.query.filter_by(usuario_id=user.id).delete(synchronize_session=False)
    for screen in CATALOG_BY_KEY:
        can_view, can_create, can_edit = normalized.get(screen, (False, False, False))
        db.session.add(UserPermission(
            usuario_id=user.id,
            tela=screen,
            pode_ver=can_view,
            pode_criar=can_create,
            pode_alterar=can_edit,
        ))
    return None


def request_permission(path, method):
    """Map protected API resources to the same screen/action matrix used by the UI."""
    method = method.upper()
    path_parts = path.strip("/").split("/")
    if (
        len(path_parts) == 3
        and path_parts[0] == "glosas"
        and path_parts[1].isdigit()
        and path_parts[2] == "evidencia"
    ):
        action = {"POST": "edit", "DELETE": "edit"}.get(method)
        return ("controle_glosas", action) if action else None

    rules = [
        ("/controle-faltas/dashboard", "dashboard_faltas", {"GET": "view"}),
        ("/controle-faltas", "controle_faltas", {"GET": "view", "POST": "edit", "PATCH": "edit"}),
        ("/glosas", "controle_glosas", {"GET": "view", "POST": "create", "PATCH": "edit", "DELETE": "edit"}),
        ("/repo/history", "historico_reposicoes", {"POST": "view", "PATCH": "edit", "DELETE": "edit"}),
        ("/repo/timeline", "historico_reposicoes", {"GET": "view"}),
        ("/repo/request/importar", "reposicoes", {"POST": "create"}),
        ("/repo/request/modelo-importacao", "reposicoes", {"GET": "view"}),
        ("/repo/request/export", "reposicoes", {"GET": "view"}),
        ("/repo/request", "reposicoes", {"GET": "view", "POST": "create", "PATCH": "edit", "DELETE": "edit"}),
        ("/repo", "reposicoes", {"POST": "edit"}),
        ("/reservas", "reservas", {"GET": "view", "POST": "create", "PATCH": "edit", "DELETE": "edit"}),
        ("/estoque/produtos", "estoque_produtos", {"GET": "view", "POST": "create", "PATCH": "edit", "DELETE": "edit"}),
        ("/estoque/movimentos/dashboard", "dashboard_logistica", {"GET": "view"}),
        ("/estoque/movimentos", "estoque_movimentos", {"GET": "view", "POST": "create", "PATCH": "edit", "DELETE": "edit"}),
        ("/admissao/vagas/dashboard", "dashboard_admissoes", {"GET": "view"}),
        ("/admissao/vagas", "admissoes", {"GET": "view", "POST": "create", "PATCH": "edit", "DELETE": "edit"}),
        ("/pcd/importar", "indicador_pcd", {"POST": "edit"}),
        ("/pcd", "indicador_pcd", {"GET": "view", "PATCH": "edit", "DELETE": "edit"}),
        ("/dash/ponto-48h", "dashboard_ponto48", {"GET": "view", "POST": "create", "DELETE": "edit"}),
        ("/dash/reposicoes", "dashboard_reposicoes", {"POST": "view"}),
        ("/dash/colaboradores-departamento", "dashboard_colaboradores", {"POST": "view"}),
        ("/projetos", "projetos", {"GET": "view", "POST": "create", "PATCH": "edit", "PUT": "edit", "DELETE": "edit"}),
        ("/estrutura", "estrutura", {"GET": "view", "POST": "create", "PATCH": "edit", "DELETE": "edit"}),
        ("/dash/pcd", "dashboard_pcd", {"GET": "view"}),
    ]
    for prefix, screen, actions in rules:
        if path == prefix or path.startswith(f"{prefix}/"):
            action = actions.get(method)
            return (screen, action) if action else None
    return None


def enforce_request_permission():
    from flask import jsonify, request

    if request.method == "OPTIONS":
        return None
    if request.path.rstrip("/") == "/repo/request" and request.method == "POST" and not request.headers.get("Access-Token"):
        return None
    required = request_permission(request.path.rstrip("/") or "/", request.method)
    if not required:
        return None
    access_token = request.headers.get("Access-Token")
    if not access_token:
        return jsonify("Token de acesso obrigatório."), 401
    try:
        token_data = decode_token(access_token)
    except Exception:
        return jsonify("Token de acesso inválido ou expirado."), 401
    screen, action = required
    if not has_permission(token_data, screen, action):
        return jsonify("Você não possui permissão para executar esta ação."), 403
    return None
