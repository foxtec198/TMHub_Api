from flask import jsonify, request
from models.cargos import Cargos
from models.situacoes import Situations
from utils.db import db

from models.colaboradores import Employees
from models.reservas_tecnicas import Floaters
from utils.filial_scope import apply_cost_center_scope, can_access_cost_center
from utils.safe_route import safe_route


class FloaterService:
    @safe_route
    def read(self, token_data):
        bd = request.args
        id = bd.get("id")
        
        rsv = (db.session.query(
            Employees.id,
            Floaters.id.label("floater_id"),
            Employees.matricula,
            Employees.nome,
            Cargos.nome.label("cargo"),
            Situations.tipo.label("situacao"),
            Floaters.created_at.label("data"),
        )
        .select_from(Floaters)
        .join(Employees, Employees.id == Floaters.employee_id)
        .join(Cargos, Cargos.id == Employees.cargo)
        .join(Situations, Situations.id == Employees.situacao))
        
        rsv = apply_cost_center_scope(rsv, Employees.centro_id, token_data)
        if id:
            row = rsv.filter(Employees.id == id).first()
            return (jsonify(row._asdict()), 200) if row else (jsonify("Reserva não encontrada"), 404)
        return jsonify([f._asdict() for f in rsv]), 200

    @safe_route
    def add(self, token_data):
        bd = request.get_json()
        id = bd.get("id")

        flt = Floaters.query.filter(Floaters.employee_id == id).first()
        if flt: return jsonify("Volante já cadastrado!"), 400
        
        clb = Employees.query.filter(Employees.id == id).first()
        if not clb:
            return jsonify("Colaborador não encontrado"), 404
        if not clb.centro_id or not can_access_cost_center(token_data, clb.centro_id):
            return jsonify("Você não possui acesso à filial deste colaborador"), 403
        db.session.add(Floaters(employee_id = id))
        db.session.commit()
        return jsonify("Sucesso"), 201
    
    @safe_route
    def remove(self, token_data):
        bd = request.args
        id = bd.get("id")
        
        floater = Floaters.query.filter(Floaters.id == id).first()
        if not floater:
            return jsonify("Reserva não encontrada"), 404
        employee = db.session.get(Employees, floater.employee_id)
        if not employee or not employee.centro_id or not can_access_cost_center(token_data, employee.centro_id):
            return jsonify("Você não possui acesso à filial desta reserva"), 403
        db.session.delete(floater)
        db.session.commit()
        return jsonify("Sucesso"), 200
