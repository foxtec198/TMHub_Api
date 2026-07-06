from flask import jsonify, request
from utils.db import db

from models.colaboradores import Employees
from models.reservas_tecnicas import Floaters


class FloaterService:
    def read(self):
        bd = request.args
        id = bd.get("id")
        if id: flts = Floaters.query.filter(Floaters.id == id).all()
        else: flts = Floaters.query.all()
        return jsonify([f.to_dict() for f in flts]), 200

    def add(self):
        bd = request.get_json()
        floater_id = bd.get("id")

        flt = Floaters.query.filter(Floaters.employee_id == id).first()
        if flt: return jsonify("Volante já cadastrado!"), 400
        
        clb = Employees.query.filter(Employees.id == floater_id).first()
        db.session.add(Floaters(employee_id = id))
        db.session.commit()
        return jsonify("Sucesso"), 201
    
    def remove(self):
        bd = request.args
        id = bd.get("id")
        
        db.session.delete(Floaters.query.filter(Floaters.id == id).first())
        db.session.commit()
        return jsonify("Sucesso"), 200
        
        

        

        
