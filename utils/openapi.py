# Utilitários de documentação OpenAPI.
# Biblioteca padrão.
import inspect
import re

# Dependências externas.
from flask import request
from werkzeug.routing import IntegerConverter, FloatConverter, UUIDConverter


METHOD_LABELS = {
    "GET": "Consultar",
    "POST": "Criar ou processar",
    "PATCH": "Atualizar",
    "PUT": "Substituir",
    "DELETE": "Excluir",
}

PUBLIC_OPERATIONS = {
    ("POST", "/login"),
    ("POST", "/repo/request"),
}

TAG_DESCRIPTIONS = {
    "Autenticador": "Autenticação e emissão de tokens.",
    "Usuarios": "Usuários, perfis, permissões e preferências.",
    "Reposições": "Requisições, histórico, timeline, importação e KDS.",
    "Controle de Faltas": "Registro, tratativa e indicadores de faltas.",
    "Controle de Glosas": "Glosas, coberturas, evidências e exportações.",
    "Estrutura": "Locais, ativos e patrimônios por contrato.",
    "Admissão": "Vagas, admissões e aditivos.",
    "Filiais": "Filiais e escopo de centros de custo.",
    "Dashboards": "Indicadores executivos e operacionais.",
    "Estoque": "Produtos, categorias e movimentações.",
    "default": "Recursos gerais da API.",
}


def _openapi_path(rule):
    return re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", rule.rule)


def _converter_schema(converter):
    if isinstance(converter, IntegerConverter):
        return {"type": "integer"}
    if isinstance(converter, FloatConverter):
        return {"type": "number", "format": "float"}
    if isinstance(converter, UUIDConverter):
        return {"type": "string", "format": "uuid"}
    return {"type": "string"}


def _tag_for_rule(app, rule):
    view = app.view_functions.get(rule.endpoint)
    blueprint_name = getattr(view, "__blueprint_name__", None)
    if blueprint_name:
        return blueprint_name
    if "." in rule.endpoint:
        blueprint_key = rule.endpoint.split(".", 1)[0]
        blueprint = app.blueprints.get(blueprint_key)
        if blueprint:
            return blueprint.name
    return "default"


def _summary(app, rule, method):
    view = app.view_functions.get(rule.endpoint)
    doc = inspect.getdoc(view) if view else None
    if doc:
        return doc.splitlines()[0][:120]
    resource = rule.rule.strip("/").split("/")[-1] or "API"
    resource = resource.replace("-", " ").replace("_", " ")
    return f"{METHOD_LABELS.get(method, method.title())} {resource}"


def _request_body(path):
    if "evidencia" in path:
        return {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "evidencia": {
                                "type": "string",
                                "format": "binary",
                                "description": "Imagem ou PDF.",
                            }
                        },
                        "required": ["evidencia"],
                    }
                }
            },
        }
    if "importar" in path:
        return {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "arquivo": {
                                "type": "string",
                                "format": "binary",
                                "description": "Planilha para importação.",
                            }
                        },
                    }
                }
            },
        }
    return {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "Consulte a regra do recurso para os campos aceitos.",
                }
            }
        },
    }


def build_openapi_spec(app):
    paths = {}
    used_tags = set()
    ignored_endpoints = {"static", "index", "docs", "openapi_spec"}

    for rule in sorted(app.url_map.iter_rules(), key=lambda item: item.rule):
        if rule.endpoint in ignored_endpoints:
            continue
        path = _openapi_path(rule)
        tag = _tag_for_rule(app, rule)
        used_tags.add(tag)

        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            operation = {
                "tags": [tag],
                "summary": _summary(app, rule, method),
                "operationId": f"{rule.endpoint.replace('.', '_')}_{method.lower()}",
                "responses": {
                    "200": {
                        "description": "Operação realizada com sucesso.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "oneOf": [
                                        {"type": "object", "additionalProperties": True},
                                        {"type": "array", "items": {"type": "object"}},
                                        {"type": "string"},
                                    ]
                                }
                            }
                        },
                    },
                    "400": {"description": "Dados inválidos."},
                    "401": {"description": "Token ausente, inválido ou expirado."},
                    "403": {"description": "Usuário sem permissão ou fora do escopo de filial."},
                    "500": {"description": "Erro interno do servidor."},
                },
            }
            if (method, rule.rule) not in PUBLIC_OPERATIONS:
                operation["security"] = [{"AccessToken": []}]
            else:
                operation["security"] = []

            parameters = []
            for argument in sorted(rule.arguments):
                parameters.append({
                    "name": argument,
                    "in": "path",
                    "required": True,
                    "schema": _converter_schema(rule._converters[argument]),
                })
            if parameters:
                operation["parameters"] = parameters

            if method in {"POST", "PUT", "PATCH", "DELETE"}:
                operation["requestBody"] = _request_body(path)
            paths.setdefault(path, {})[method.lower()] = operation

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "TM Hub API",
            "version": "1.0.0",
            "description": (
                "Documentação gerada automaticamente a partir das rotas Flask. "
                "As operações autenticadas usam o cabeçalho `Access-Token`. "
                "Usuários comuns permanecem limitados às filiais vinculadas."
            ),
        },
        "servers": [{"url": request.url_root.rstrip("/"), "description": "Servidor atual"}],
        "tags": [
            {"name": tag, "description": TAG_DESCRIPTIONS.get(tag, TAG_DESCRIPTIONS["default"])}
            for tag in sorted(used_tags)
        ],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "AccessToken": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "Access-Token",
                    "description": "JWT obtido em `POST /login`.",
                }
            }
        },
    }
