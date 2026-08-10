from flask import Blueprint

from services.timo import TimoCommandService


timo_bp = Blueprint("Timo", __name__)
service = TimoCommandService()


@timo_bp.post("/comandos")
def commands():
    return service.process()
