# Models
from models.centros_de_custo import CostCenters, db
from models.rp_requisicao import Requisicao
from models.rp_timeline import Timeline
from models.supervisores import Supervisors
from models.colaboradores import Employees
from models.rp_historico import History
from models.cargos import Cargos

# Utils
from datetime import datetime as dt
from dateutils import relativedelta
from flask import jsonify, request
from utils.socket import socketio
from calendar import monthrange
from sqlalchemy import case
from utils.check_field import check_field
from utils.safe_route import safe_route
from sqlalchemy.orm import aliased

class RequestService:
    @safe_route
    def read(self):
        bd = request.args
        
        limit = bd.get("limit", None)
        id = bd.get("id", None)
        status = bd.get("status", "pending")

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
            .filter(Requisicao.status == status)
        )
        
        if id: reqs.filter(Requisicao.id == id)
        if limit: reqs.limit(limit=limit)
        reqs = reqs.all()
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
        status = "pending"

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
            motivo=motivo,
            status=status
        )

        if data: new_rq.created_at = data
        if obs: new_rq.obs = str(obs).strip().upper()
        db.session.add(new_rq)
        db.session.commit()

        TimelineService().create_event(
            req=new_rq,
            status=status,
            tipo="Criação da requisição",
            obs=obs
        )
        
        socketio.emit("new_request")
        return jsonify("Requisição criada"), 201

    def update(self):
        bd = request.get_json()
        id = bd.get("id")

        req = Requisicao.query.filter(Requisicao.id == id).first()
        if not req: return jsonify("Requisição não encontrada"), 404

        if "reserva_id" in bd: req.reserva_id = bd.get("reserva_id")
        if "centro_id" in bd: req.cc = bd.get("centro_id")
        if "ausente_id" in bd: req.ausente_id = bd.get("ausente_id")
        if "motivo" in bd: req.motivo = bd.get("motivo")
        db.session.commit()

        TimelineService().create_event(
            req=req,
            status="updated",
            tipo="Alteração de Dados",
            obs=bd.get("obs", req.obs)
        )

        socketio.emit("new_request")
        return jsonify("Requisição alterada"), 200
        
class HistoryService:
    @safe_route
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
        
    @safe_route
    def create(self):
        bd = request.get_json()
        id = bd.get("id")
        status = bd.get("status", "reproved")
        req = Requisicao.query.filter(Requisicao.id == id).first()

        requisicao_id = req.id
        reserva_id = req.reserva_id if status == "approved" else 0
        ausente_id = req.ausente_id
        cc_id = req.cc
        created_at = req.created_at
        supervisor_id = req.supervisor_id
        motivo = req.motivo
        ended_at = dt.now()
        obs = req.obs

        db.session.add(
            History(
                requisicao_id=requisicao_id,
                reserva_id=reserva_id,
                ausente_id=ausente_id,
                cc=cc_id,
                status=status,
                created_at=created_at,
                ended_at=ended_at,
                supervisor_id=supervisor_id,
                motivo=motivo,
                obs=obs
            )
        )
        
        req.status = status
        req.reserva_id = reserva_id
        db.session.commit()
        
        TimelineService().create_event(
            req= req,
            status= status,
            tipo = "Aprovado" if status == "approved" else "Reprovado, posto sem cobertura.",
            obs= obs
        )

        socketio.emit("new_history")
        return jsonify("Sucesso"), 201

class TimelineService:
    def create_event(self, req, status, tipo, obs=None):
        db.session.add(
            Timeline(
                requisicao_id=req.id,
                reserva_id=req.reserva_id,
                ausente_id=req.ausente_id,
                cc=req.cc,
                supervisor_id=req.supervisor_id,
                status=status,
                tipo=tipo,
                motivo=req.motivo,
                obs=obs or req.obs
            )
        )
        db.session.commit()

    def read(self):
        requisicao_id = request.args.get("requisicao_id")

        Ausente = aliased(Employees)
        Reserva = aliased(Employees)

        query = (
            db.session.query(
                Timeline.id,
                Timeline.requisicao_id,
                Timeline.created_at,
                Timeline.status,
                Timeline.tipo,
                Ausente.nome.label("ausente"),
                case(
                    (Timeline.reserva_id == 0, "SEM COBERTURA"),
                    else_=Reserva.nome
                ).label("reserva"),
                CostCenters.local,
                Supervisors.nome.label("supervisor"),
                Timeline.motivo,
                Timeline.obs,
            )
            .select_from(Timeline)
            .join(Ausente, Ausente.id == Timeline.ausente_id)
            .outerjoin(Reserva, Reserva.id == Timeline.reserva_id)
            .join(CostCenters, CostCenters.id == Timeline.cc)
            .join(Supervisors, Supervisors.id == Timeline.supervisor_id)
            .order_by(Timeline.created_at.desc())
        )

        if requisicao_id: query = query.filter(Timeline.requisicao_id == requisicao_id)
        timelines = query.all()
        return jsonify([t._asdict() for t in timelines]), 200
