from flask import request as rq, jsonify
from utils.safe_route import safe_route
from models.centros_de_custo import CostCenters
from models.cidades import Cities
from utils.settings import ALLOW_CITIES
from utils.filial_scope import apply_cost_center_scope
from utils.token import decode_token

class CostsCenterService():
    def read(self):
        id = rq.args.get("id")

        if id:
            cost = CostCenters().query.filter_by(id=id).first()
            return jsonify(cost), 200 if cost else jsonify("Centro de custo não encontrado"), 404
        
        costs_query = CostCenters().query.join(Cities, Cities.id == CostCenters.cidade_id).filter(Cities.descricao.in_(ALLOW_CITIES))
        access_token = rq.headers.get("Access-Token")
        if access_token:
            costs_query = apply_cost_center_scope(costs_query, CostCenters.id, decode_token(access_token))
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
