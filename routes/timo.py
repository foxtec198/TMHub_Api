from flask import Blueprint

from services.timo import TimoCommandService


timo_bp = Blueprint("Timo", __name__)
service = TimoCommandService()


@timo_bp.post("/process")
def process():
    return service.process()


@timo_bp.get("/configuracoes")
def configurations():
    return service.read_configurations()


@timo_bp.patch("/configuracoes/<string:intent>")
def update_configuration(intent):
    return service.update_configuration(intent=intent)


@timo_bp.post("/configuracoes/comandos")
def create_custom_command():
    return service.create_custom_command()


@timo_bp.delete("/configuracoes/<string:intent>")
def delete_custom_command(intent):
    return service.delete_custom_command(intent=intent)
