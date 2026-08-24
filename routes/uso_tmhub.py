"""Rotas do controle de uso e Edinhos."""

from flask import Blueprint

from services.uso_tmhub import TMHubUsageService


usage_bp = Blueprint("Uso TMHub", __name__)
service = TMHubUsageService()


@usage_bp.post("/atividade")
def activity():
    return service.activity()


@usage_bp.get("")
def read():
    return service.read()


@usage_bp.get("/meu-dia")
def my_day():
    return service.my_day()
