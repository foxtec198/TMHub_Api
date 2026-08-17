# Rotas HTTP de chamados.
# Dependências externas.
from flask import Blueprint

# Módulos internos da aplicação.
from services.tickets import TicketService


tickets_bp = Blueprint("Tickets", __name__)
service = TicketService()


@tickets_bp.get("")
def read():
    return service.read()


@tickets_bp.post("")
def create():
    return service.create()


@tickets_bp.get("/motivos")
def reasons():
    return service.reasons()


@tickets_bp.post("/motivos")
def create_reason():
    return service.create_reason()


@tickets_bp.patch("/motivos/<int:reason_id>")
def update_reason(reason_id):
    return service.update_reason(reason_id)


@tickets_bp.get("/responsaveis")
def assignees():
    return service.assignees()


@tickets_bp.post("/teste-email")
def test_email():
    return service.test_email()


@tickets_bp.get("/<int:ticket_id>")
def detail(ticket_id):
    return service.detail(ticket_id)


@tickets_bp.patch("/<int:ticket_id>")
def update(ticket_id):
    return service.update(ticket_id)


@tickets_bp.post("/<int:ticket_id>/comentarios")
def add_comment(ticket_id):
    return service.add_comment(ticket_id)
