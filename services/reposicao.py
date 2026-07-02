from flask import jsonify, request
from utils.check_field import check_field
from utils.safe_route import safe_route
from sqlalchemy.orm import aliased

from models.colaboradores import Employees
from models.centros_de_custo import CostCenters
from models.supervisores import Supervisors
from models.reposicoes import History, Requisicao, db
from utils.socket import socketio

class ReplaceService:
    @safe_route
    def read(self):
        ...
    
    @safe_route
    def create(self): 
        ...
        
class RequestService:
    def read(self):
        Ausente = aliased(Employees)
        Reserva = aliased(Employees)

        reqs = db.session.query(
            Requisicao.created_at.label("data"),
            Ausente.nome.label("ausencia"),
            Reserva.nome.label("reserva"),
            CostCenters.local,
            Supervisors.nome.label("supervisor"),
            Requisicao.warning,
            Requisicao.motivo
        ).join(
            Ausente, Ausente.id == Requisicao.ausente_id
        ).join(
            Reserva, Reserva.id == Requisicao.reserva_id
        ).join(
            CostCenters, CostCenters.id == Requisicao.cc
        ).join(
            Supervisors, Supervisors.id == Requisicao.supervisor_id
        ).order_by(
            Requisicao.created_at.desc()
        ).all()
        
        return jsonify([r._asdict() for r in reqs]), 200
    
    def create(self):
        bd = request.get_json()

        supervisor_id = bd.get("supervisor_id")
        reserva_id = bd.get("reserva_id")
        centro_id = bd.get("centro_id")
        ausente_id = bd.get("ausente_id")
        advertencia = str(bd.get("advertencia"))
        motivo = bd.get("motivo")

        ok, error = check_field(
            Supervisor=supervisor_id, 
            Reserva=reserva_id,
            Local=centro_id,
            Ausente=ausente_id,
            Motivo=motivo
        )

        adv = True if advertencia and advertencia.lower() == "aplicado" else False
        
        if not ok: return jsonify(error), 400

        new_rq = Requisicao(
            reserva_id=reserva_id, ausente_id=ausente_id, 
            cc=centro_id, supervisor_id=supervisor_id, warning=adv,
            motivo=motivo
        )
        
        db.session.add(new_rq)
        db.session.commit()
        socketio.emit("new_request")
        
        return jsonify("Requisição criada"), 201
