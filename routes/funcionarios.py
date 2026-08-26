"""Rotas do cadastro de colaboradores."""
from flask import Blueprint, request

from services.funcionarios import EmployeesService

funcionarios_bp = Blueprint("Funcionarios", __name__)
service = EmployeesService()


@funcionarios_bp.get("")
def root():
    return service.read()


@funcionarios_bp.get("/filtros")
def filters():
    return service.filters()


@funcionarios_bp.get("/exportar")
def export():
    return service.export()


@funcionarios_bp.patch("/<int:employee_id>")
def update(employee_id):
    return service.update(employee_id)
