# Rotas HTTP de atualizações.
# Dependências externas.
from flask import Blueprint

# Módulos internos da aplicação.
from services.github_updates import GitHubUpdatesService
from services.noticias import LoginNewsService


updates_bp = Blueprint("Atualizações públicas", __name__)
service = GitHubUpdatesService()
news_service = LoginNewsService()


@updates_bp.get("/github")
def github_updates():
    return service.read()


@updates_bp.get("/noticias")
def public_news():
    return news_service.public_read()


@updates_bp.get("/noticias/admin")
def admin_news():
    return news_service.admin_read()


@updates_bp.post("/noticias")
def create_news():
    return news_service.create()


@updates_bp.put("/noticias/<int:news_id>")
def update_news(news_id):
    return news_service.update(news_id)


@updates_bp.delete("/noticias/<int:news_id>")
def delete_news(news_id):
    return news_service.delete(news_id)
