from flask import jsonify, request as rq
from models.supervisores import Supervisors, db
from models.centros_de_custo import CostCenters
from utils.safe_route import safe_route
from utils.check_field import check_field
from utils.filial_scope import apply_cost_center_scope, is_admin
from utils.token import decode_token

class ServiceSupervisors():
    def read(self):
        query = Supervisors.query
        access_token = rq.headers.get("Access-Token")
        if access_token:
            token_data = decode_token(access_token)
            if not is_admin(token_data):
                query = query.join(
                    CostCenters, CostCenters.supervisor_id == Supervisors.id
                ).distinct()
                query = apply_cost_center_scope(
                    query, CostCenters.id, token_data
                )
        sups = query.order_by(Supervisors.nome).all()
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
