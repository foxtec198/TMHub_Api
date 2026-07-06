from flask import jsonify
from models.cargos import Cargos
from models.situacoes import Situations
from utils.safe_route import safe_route

from models.centros_de_custo import CostCenters
from models.cidades import Cities
from models.colaboradores import Employees, db

class EmployeesService:
    def read(self):
        emp = (Employees.query
        .join(Cargos, Cargos.id == Employees.cargo)
        .join(Situations, Situations.id == Employees.situacao)
        .all())
        return jsonify([e.to_dict() for e in emp]), 200

    @safe_route
    def create(self): ...

    @safe_route
    def update(self): ...

    @safe_route
    def delete(self): ...