from flask import jsonify, request

from models.noticias import LoginNews
from models.usuarios import Users
from utils.db import db
from utils.safe_route import safe_route


DEFAULT_LOGIN_NEWS = (
    {
        "chamada": "Operação conectada",
        "titulo": "Reposições acompanhadas em tempo real.",
        "descricao": "Acompanhe solicitações, reservas e decisões sem precisar atualizar a página.",
        "icone": "pi pi-sync",
        "cor_destaque": "#64ea8a",
        "ordem": 1,
    },
    {
        "chamada": "Gestão centralizada",
        "titulo": "Informações importantes em um único painel.",
        "descricao": "Faltas, admissões, glosas, estoque e indicadores trabalhando de forma integrada.",
        "icone": "pi pi-chart-line",
        "cor_destaque": "#56d9bd",
        "ordem": 2,
    },
    {
        "chamada": "Precisa de ajuda?",
        "titulo": "A nova central de suporte está disponível.",
        "descricao": "Acesse orientações e a documentação técnica diretamente pela página inicial.",
        "icone": "pi pi-headphones",
        "cor_destaque": "#9ae765",
        "ordem": 3,
    },
)


def seed_default_news():
    if LoginNews.query.first():
        return
    db.session.add_all(LoginNews(ativo=True, **item) for item in DEFAULT_LOGIN_NEWS)
    db.session.commit()


def _serialize(item):
    return {
        "id": item.id,
        "eyebrow": item.chamada,
        "title": item.titulo,
        "description": item.descricao,
        "icon": item.icone,
        "accent": item.cor_destaque,
        "image": item.imagem,
        "link": item.link,
        "order": item.ordem,
        "active": item.ativo,
        "created_at": item.criado_em.isoformat() if item.criado_em else None,
        "updated_at": item.atualizado_em.isoformat() if item.atualizado_em else None,
    }


def _admin(token_data):
    user = db.session.get(Users, (token_data or {}).get("id"))
    return bool(user and str(user.role or "").upper() == "ADMIN")


def _text(body, key, maximum=None):
    value = str(body.get(key) or "").strip()
    return value[:maximum] if maximum else value


class LoginNewsService:
    def public_read(self):
        items = (
            LoginNews.query.filter_by(ativo=True)
            .order_by(LoginNews.ordem, LoginNews.id)
            .all()
        )
        return jsonify([_serialize(item) for item in items])

    @safe_route
    def admin_read(self, token_data):
        if not _admin(token_data):
            return jsonify("Somente administradores podem gerenciar as notícias."), 403
        items = LoginNews.query.order_by(LoginNews.ordem, LoginNews.id).all()
        return jsonify([_serialize(item) for item in items])

    @safe_route
    def create(self, token_data):
        if not _admin(token_data):
            return jsonify("Somente administradores podem gerenciar as notícias."), 403
        body = request.get_json(silent=True) or {}
        title = _text(body, "title", 180)
        description = _text(body, "description")
        if not title or not description:
            return jsonify("Informe o título e a descrição da notícia."), 400
        item = LoginNews(
            chamada=_text(body, "eyebrow", 120) or "Novidades",
            titulo=title,
            descricao=description,
            icone=_text(body, "icon", 80) or "pi pi-megaphone",
            cor_destaque=_text(body, "accent", 20) or "#64ea8a",
            imagem=body.get("image") or None,
            link=_text(body, "link") or None,
            ordem=int(body.get("order") or 0),
            ativo=bool(body.get("active", True)),
        )
        db.session.add(item)
        db.session.commit()
        return jsonify(_serialize(item)), 201

    @safe_route
    def update(self, news_id, token_data):
        if not _admin(token_data):
            return jsonify("Somente administradores podem gerenciar as notícias."), 403
        item = db.session.get(LoginNews, news_id)
        if not item:
            return jsonify("Notícia não encontrada."), 404
        body = request.get_json(silent=True) or {}
        title = _text(body, "title", 180)
        description = _text(body, "description")
        if not title or not description:
            return jsonify("Informe o título e a descrição da notícia."), 400
        item.chamada = _text(body, "eyebrow", 120) or "Novidades"
        item.titulo = title
        item.descricao = description
        item.icone = _text(body, "icon", 80) or "pi pi-megaphone"
        item.cor_destaque = _text(body, "accent", 20) or "#64ea8a"
        item.imagem = body.get("image") or None
        item.link = _text(body, "link") or None
        item.ordem = int(body.get("order") or 0)
        item.ativo = bool(body.get("active", True))
        db.session.commit()
        return jsonify(_serialize(item))

    @safe_route
    def delete(self, news_id, token_data):
        if not _admin(token_data):
            return jsonify("Somente administradores podem gerenciar as notícias."), 403
        item = db.session.get(LoginNews, news_id)
        if not item:
            return jsonify("Notícia não encontrada."), 404
        db.session.delete(item)
        db.session.commit()
        return "", 204
