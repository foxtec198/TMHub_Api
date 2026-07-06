from flask import jsonify, request
from models.cargos import Cargos
from models.situacoes import Situations
from utils.db import db

from models.colaboradores import Employees
from models.reservas_tecnicas import Floaters


class FloaterService:
    def read(self):
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
        
        if id: return jsonify(rsv.filter(Employees.id == id).first()._asdict())
        return jsonify([f._asdict() for f in rsv]), 200

    def add(self):
        bd = request.get_json()
        id = bd.get("id")

        flt = Floaters.query.filter(Floaters.employee_id == id).first()
        if flt: return jsonify("Volante já cadastrado!"), 400
        
        clb = Employees.query.filter(Employees.id == id).first()
        db.session.add(Floaters(employee_id = id))
        db.session.commit()
        return jsonify("Sucesso"), 201
    
    def remove(self):
        bd = request.args
        id = bd.get("id")
        
        db.session.delete(Floaters.query.filter(Floaters.id == id).first())
        db.session.commit()
        return jsonify("Sucesso"), 200