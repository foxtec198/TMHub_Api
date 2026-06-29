from flask import jsonify
from models.colaboradores import Employees, db
from utils.safe_route import safe_route

class EmployeesService:
    def read(self):
        emp = Employees.query.all()
        return jsonify([e.to_dict() for e in emp]), 200

    @safe_route
    def create(self): ...

    @safe_route
    def update(self): ...

    @safe_route
    def delete(self): ...