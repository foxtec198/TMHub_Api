from flask import jsonify, request as rq
from models.supervisores import Supervisors, db
from utils.safe_route import safe_route
from utils.check_field import check_field

class ServiceSupervisors():
    def read(self):
        sups = Supervisors().query.all()
        return jsonify([s.to_dict() for s in sups]), 200
    
    @safe_route
    def create(self):
        body = rq.get_json()
        nome = body.get("nome")
        
        ok, error = check_field(nome=nome)
        if not ok: return jsonify(error), 400 
        
        if len(nome.split(" ")) < 1: return jsonify("Nome completo obrgatorio"), 400

        new_sup = Supervisors(nome=nome.upper())
        db.session.add(new_sup)
        db.session.commit()
        return jsonify("Supervisor criado com sucesso"), 201