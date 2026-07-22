from flask import jsonify, request as rq
from models.cargos import Cargos
from models.centros_de_custo import CostCenters
from models.situacoes import Situations
from utils.safe_route import safe_route
from sqlalchemy import or_, cast
from models.colaboradores import Employees, db
from utils.filial_scope import apply_cost_center_scope
from utils.token import decode_token

class EmployeesService:
    def read(self):
        search_fields = [
            Employees.nome,
            Employees.matricula,
            Cargos.nome,
            Situations.tipo,
            CostCenters.local,
        ]

        bd = rq.args
        situation_id = bd.get("situacao", None)
        limit = bd.get("limit")
        search = bd.get("search")

        emp = (
            db.session.query(
                Employees.id,
                Employees.matricula,
                Employees.nome,
                Employees.data_admissao,
                Employees.centro_id,
                CostCenters.local.label("centro_local"),
                CostCenters.departamento,
                Cargos.nome.label("cargo"),
                Situations.tipo.label("situacao"),
            )
            .select_from(Employees)
            .join(Cargos, Cargos.id == Employees.cargo)
            .join(Situations, Situations.id == Employees.situacao)
            .outerjoin(CostCenters, CostCenters.id == Employees.centro_id)
            .order_by(Employees.data_admissao.desc())
        )

        access_token = rq.headers.get("Access-Token")
        if access_token:
            emp = apply_cost_center_scope(emp, Employees.centro_id, decode_token(access_token))

        if situation_id:emp = emp.filter(Situations.id == int(situation_id))  # Se passado o filtro de situacao
        if search: emp = emp.filter(or_(*[field.ilike(f"%{search}%") for field in search_fields]))
        if limit: emp = emp.limit(limit)
            
        emp = emp.all()  # Obtem tudo
        return jsonify([e._asdict() for e in emp]), 200

    @safe_route
    def create(self): ...

    @safe_route
    def update(self): ...

    @safe_route
    def delete(self): ...
