# Regras de negócio de supervisores.
# Dependências externas.
from flask import jsonify, request as rq
# Módulos internos da aplicação.
from models.supervisores import Supervisors, db
from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from utils.safe_route import safe_route
from utils.check_field import check_field
from utils.filial_scope import apply_active_department_scope, apply_cost_center_scope
from utils.token import decode_token

class ServiceSupervisors():
    def read(self):
        query = Supervisors.query.join(
            CostCenters, CostCenters.supervisor_id == Supervisors.id
        ).distinct()
        center_id = rq.args.get("centro_id", type=int)
        if rq.args.get("centro_id") and not center_id:
            return jsonify("Local selecionado inválido."), 400
        if center_id:
            query = query.filter(CostCenters.id == center_id)
        access_token = rq.headers.get("Access-Token")
        if access_token:
            token_data = decode_token(access_token)
            query = apply_cost_center_scope(query, CostCenters.id, token_data)
        else:
            query = apply_active_department_scope(query, CostCenters.id)
        sups = query.order_by(Supervisors.nome).all()
        return jsonify([s.to_dict() for s in sups]), 200
    
    @safe_route
    def create(self):
        body = rq.get_json()
        nome = body.get("nome")
        colaborador_id = body.get("colaborador_id") or None
        
        ok, error = check_field(nome=nome)
        if not ok: return jsonify(error), 400 
        
        if len(nome.split(" ")) < 1: return jsonify("Nome completo obrgatorio"), 400

        if colaborador_id:
            employee = db.session.get(Employees, colaborador_id)
            if not employee:
                return jsonify("Colaborador não encontrado"), 404
            if Supervisors.query.filter_by(colaborador_id=employee.id).first():
                return jsonify("Este colaborador já está vinculado a um supervisor"), 400
            colaborador_id = employee.id

        new_sup = Supervisors(
            nome=nome.upper(),
            colaborador_id=colaborador_id,
        )
        db.session.add(new_sup)
        db.session.commit()
        return jsonify("Supervisor criado com sucesso"), 201
