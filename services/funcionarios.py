from flask import jsonify, request as rq
from models.cargos import Cargos
from models.situacoes import Situations
from utils.safe_route import safe_route

from models.centros_de_custo import CostCenters
from models.cidades import Cities
from models.colaboradores import Employees, db

class EmployeesService:
    def read(self):
        bd = rq.args
        situation_id = bd.get("situacao", None)

        emp = (db.session.query(
            Employees.id,
            Employees.matricula,
            Employees.nome,
            Employees.data_admissao,
            Cargos.nome.label("cargo"),
            Situations.tipo.label("situacao"),
        ).select_from(Employees)
        .join(Cargos, Cargos.id == Employees.cargo)
        .join(Situations, Situations.id == Employees.situacao))

        if situation_id: emp = emp.filter(Situations.id == int(situation_id)) # Se passado o filtro de situacao
        emp = emp.all() # Obtem tudo
        return jsonify([e._asdict() for e in emp]), 200

    @safe_route
    def create(self): ...

    @safe_route
    def update(self): ...

    @safe_route
    def delete(self): ...