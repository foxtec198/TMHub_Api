# Rotas HTTP de setores.
from flask import Blueprint
from services.setores import SectorService


setores_bp = Blueprint("Setores", __name__)
service = SectorService()


@setores_bp.get("")
def read():
    return service.read()


@setores_bp.post("")
def create():
    return service.create()


@setores_bp.patch("/<int:sector_id>")
def update(sector_id):
    return service.update(sector_id)
