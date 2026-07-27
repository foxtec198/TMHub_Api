from flask import request as rq, jsonify
from utils.safe_route import safe_route
from models.centros_de_custo import CostCenters
from utils.filial_scope import apply_cost_center_scope, can_access_cost_center

class CostsCenterService():
    @safe_route
    def read(self, token_data):
        id = rq.args.get("id")

        if id:
            if not can_access_cost_center(token_data, int(id)):
                return jsonify("Você não possui acesso à filial deste centro de custo"), 403
            cost = CostCenters().query.filter_by(id=id).first()
            return jsonify(cost), 200 if cost else jsonify("Centro de custo não encontrado"), 404
        
        costs_query = CostCenters.query
        costs_query = apply_cost_center_scope(
            costs_query, CostCenters.id, token_data
        )
        costs = costs_query.all()
        return jsonify([c.to_dict() for c in costs])
        
    @safe_route
    def create(self):
        ...
        
    @safe_route
    def update(self):
        ...

    @safe_route
    def delete(self):
        ...
