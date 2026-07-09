from flask import jsonify, request
from models.cargos import Cargos
from utils.check_field import check_field
from utils.safe_route import safe_route
from sqlalchemy.orm import aliased
from models.colaboradores import Employees
from models.centros_de_custo import CostCenters
from models.supervisores import Supervisors
from models.reposicoes import History, Requisicao, db
from utils.socket import socketio
from sqlalchemy import case
from datetime import datetime as dt
from dateutils import relativedelta
from calendar import monthrange

class ReplaceService:
    # @safe_route
    def read(self):
        bd = request.get_json()

        init = bd.get("init", None)
        end = bd.get("end", None)
        
        if init and end: # Se passar os dois
            init = dt.now().strptime(init, "%d/%m/%Y").replace(hour=0, minute=0, second=0); 
            end = dt.now().strptime(end, "%d/%m/%Y").replace(hour=23, minute=59, second=59)
        elif init: # Se for passado somente o init
            init = dt.now().strptime(init, "%d/%m/%Y").replace(hour=0, minute=0, second=0); 
            end = init.replace(hour=23, minute=59, second=59)
        else: # Se nao for passado nenhum
            init = dt.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0); 
            dias_no_mes = monthrange(init.year, init.month)[1]
            end = init + relativedelta(day=dias_no_mes , hour=23, minute=59, second=59)
        
        Ausente = aliased(Employees)
        Reserva = aliased(Employees)
        hists = (
            db.session.query(
                History.id,
                History.created_at.label("abertura"),
                Ausente.nome.label("ausente"),
                case(
                    (History.reserva_id == 0, "SEM COBERTURA"), else_=Reserva.nome
                ).label("reserva"),
                History.motivo,
                History.obs,
                Supervisors.nome.label("supervisor"),
                CostCenters.local.label("local"),
                CostCenters.departamento.label("dpto"),
                History.status,
                Cargos.multa,
                
            )
            .select_from(History)
            .join(Ausente, Ausente.id == History.ausente_id)
            .outerjoin(Reserva, Reserva.id == History.reserva_id)
            .outerjoin(Cargos, Cargos.id == Reserva.cargo)
            .join(CostCenters, CostCenters.id == History.cc)
            .join(Supervisors, Supervisors.id == History.supervisor_id)
            .filter(History.created_at.between(init, end))
            .order_by(History.created_at.desc())
            .all()
        )
        return jsonify([h._asdict() for h in hists]), 200

    def create(self):
        bd = request.get_json()
        id = bd.get("id")
        status = bd.get("status", "reproved")
        req = Requisicao.query.filter(Requisicao.id == id).first()

        requisicao_id = req.id
        reserva_id = req.reserva_id if status == "approved" else 0
        ausente_id = req.ausente_id
        cc_id = req.cc
        status = status
        created_at = req.created_at
        supervisor_id = req.supervisor_id
        motivo = req.motivo
        ended_at = dt.now()
        obs = req.obs

        db.session.add(
            History(
                requisicao_id=requisicao_id,
                reserva_id=reserva_id,
                ausente_id = ausente_id,
                cc = cc_id, status=status,
                created_at=created_at,
                ended_at=ended_at,
                supervisor_id=supervisor_id,
                motivo=motivo, obs=obs
            )
        )

        db.session.delete(req)
        db.session.commit()
        socketio.emit("new_request")
        return jsonify("Sucesso"), 201

class RequestService:
    def read(self):
        Ausente = aliased(Employees)
        Reserva = aliased(Employees)

        reqs = (
            db.session.query(
                Requisicao.id,
                Requisicao.created_at.label("data"),
                Ausente.nome.label("ausencia"),
                case(
                    (Requisicao.reserva_id == 0, "SEM COBERTURA"), else_=Reserva.nome
                ).label("reserva"),
                CostCenters.local,
                Supervisors.nome.label("supervisor"),
                Requisicao.warning,
                Requisicao.motivo,
            )
            .select_from(Requisicao)
            .join(Ausente, Ausente.id == Requisicao.ausente_id)
            .outerjoin(Reserva, Reserva.id == Requisicao.reserva_id)
            .join(CostCenters, CostCenters.id == Requisicao.cc)
            .join(Supervisors, Supervisors.id == Requisicao.supervisor_id)
            .order_by(Requisicao.created_at.desc())
            .all()
        )

        return jsonify([r._asdict() for r in reqs]), 200

    def create(self):
        bd = request.get_json()

        supervisor_id = bd.get("supervisor_id")
        reserva_id = bd.get("reserva_id")
        centro_id = bd.get("centro_id")
        ausente_id = bd.get("ausente_id")
        advertencia = str(bd.get("advertencia"))
        motivo = bd.get("motivo")
        data = bd.get("data")
        obs = bd.get("obs")

        ok, error = check_field(
            Supervisor=supervisor_id, Local=centro_id, Ausente=ausente_id, Motivo=motivo
        )

        if not ok:
            return jsonify(error), 400
        adv = True if advertencia and advertencia.lower() == "aplicado" else False

        new_rq = Requisicao(
            reserva_id=reserva_id,
            ausente_id=ausente_id,
            cc=centro_id,
            supervisor_id=supervisor_id,
            warning=adv,
            motivo=motivo
        )

        if data: new_rq.created_at = data
        if obs: new_rq.obs = str(obs).strip().upper()

        db.session.add(new_rq)
        db.session.commit()
        socketio.emit("new_request")
        return jsonify("Requisição criada"), 201
