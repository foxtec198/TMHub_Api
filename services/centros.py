from flask import request as rq, jsonify
from models.centros_de_custo import CostCenters
from utils.safe_route import safe_route

class CostsCenterService():
    def read(self):
        id = rq.args.get("id")

        if id:
            cost = CostCenters().query.filter_by(id=id).first()
            return jsonify(cost), 200 if cost else jsonify("Centro de custo não encontrado"), 404
        
        costs = CostCenters().query.all()
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