# Utilitários de tratamento seguro de rotas.
# Biblioteca padrão.
import inspect
from functools import wraps

# Dependências externas.
from flask import g, jsonify, request as rq
from jwt import ExpiredSignatureError

# Módulos internos da aplicação.
from utils.socket import socketio
from utils.token import decode_token


MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _response_status(result):
    if isinstance(result, tuple) and len(result) > 1 and isinstance(result[1], int):
        return result[1]
    return getattr(result, "status_code", 200)


def _data_channel(path, method):
    """Map mutations to the screen domain that owns the changed data."""
    if path == "/repo" or path.startswith("/repo/request"):
        return "reposicoes.requisicoes"
    if path.startswith("/repo/history") and method in {"PATCH", "DELETE"}:
        return "reposicoes.historico"
    if path.startswith("/reservas"):
        return "reposicoes.reservas"
    if path.startswith(("/estoque/produtos", "/estoque/categorias")):
        return "estoque.produtos"
    if path.startswith("/estoque/movimentos"):
        return "dashboard.logistica" if path.endswith("/dashboard") else "estoque.movimentos"
    if path.startswith("/admissao/vagas"):
        return "admissao"
    if path.startswith("/rescisoes"):
        return "rescisoes"
    if path == "/controle-faltas":
        return "controle_faltas"
    if path.startswith("/medidas-disciplinares"):
        return "medidas_disciplinares"
    if path.startswith("/glosas"):
        return "glosas"
    if path.startswith("/arquivos/glosas"):
        return "glosas"
    if path.startswith("/projetos"):
        return "projetos"
    if path.startswith("/tickets"):
        return "tickets"
    if path.startswith("/estrutura"):
        return "estrutura"
    if path.startswith("/pcd"):
        return "pcd"
    if path.startswith("/dash/ponto-48h"):
        return "ponto48"
    if path.startswith("/updates/noticias"):
        return "configuracoes"
    if path.startswith("/timo"):
        return "configuracoes"
    if path.startswith(("/tm-ops", "/scheduler")):
        return "tm_ops"
    if path.startswith("/rpa"):
        return "rpa"
    if path.startswith(("/importacao-colaboradores", "/update")):
        return "colaboradores"
    if path in {"/usuarios", "/usuarios/importar", "/filiais", "/centro", "/centro/configuracoes", "/supervisores", "/funcionarios"}:
        return "configuracoes"
    if path.startswith("/avaliacoes-experiencia"):
        return "avaliacoes_experiencia"
    return None


def _emit_data_change(token_data, channel):
    try:
        socketio.emit(
            "data_changed",
            {
                "path": rq.path,
                "method": rq.method,
                "channel": channel,
                "resource": rq.path.strip("/").split("/", 1)[0] or "root",
                "source_socket": rq.headers.get("X-TMHub-Socket-Id"),
                "user_id": token_data.get("id"),
            },
        )
    except Exception:
        # Realtime is complementary: a socket failure must never roll back or
        # report failure for a mutation that was already committed.
        return


def safe_route(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        access_token = rq.headers.get("Access-Token")
        if not access_token: return jsonify("Token de acesso obrigatorio"), 400
        # try:
        token_data = decode_token(access_token)
        signature = inspect.signature(func)
        if "token_data" in signature.parameters:
            kwargs["token_data"] = token_data

        result = func(*args, **kwargs)
        channel = _data_channel(rq.path, rq.method)
        if (
            rq.method in MUTATION_METHODS
            and _response_status(result) < 400
            and channel
        ):
            _emit_data_change(token_data, channel)
            g.tmhub_data_change_emitted = True
        return result
        # except ExpiredSignatureError:
        #     return jsonify("Token de acesso expirado"), 401
        # except Exception as error:
        #     try:
        #         from utils.db import db
        #         db.session.rollback()
        #     except Exception:
        #         pass
        #     return jsonify("Erro com o servidor: " + str(error)), 500
    return wrapper
