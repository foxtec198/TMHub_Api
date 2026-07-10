# Models
from models.centros_de_custo import CostCenters, db
from models.rp_requisicao import Requisicao
from models.rp_timeline import Timeline
from models.supervisores import Supervisors
from models.colaboradores import Employees
from models.rp_historico import History
from models.cargos import Cargos
from models.usuarios import Users

# Utils
from datetime import datetime as dt
from dateutils import relativedelta
from flask import jsonify, request
from utils.socket import socketio
from calendar import monthrange
from sqlalchemy import case, func
from utils.check_field import check_field
from utils.safe_route import safe_route
from sqlalchemy.orm import aliased

class RequestService:
    @safe_route
    def read(self):
        bd = request.args
        
        limit = bd.get("limit", None)
        id = bd.get("id", None)
        status = bd.get("status")

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
                Requisicao.status,
            )
            .select_from(Requisicao)
            .join(Ausente, Ausente.id == Requisicao.ausente_id)
            .outerjoin(Reserva, Reserva.id == Requisicao.reserva_id)
            .join(CostCenters, CostCenters.id == Requisicao.cc)
            .join(Supervisors, Supervisors.id == Requisicao.supervisor_id)
            .order_by(Requisicao.created_at.desc())
        )
        
        if id: reqs = reqs.filter(Requisicao.id == id)
        if status:
            statuses = [s.strip() for s in status.split(",") if s.strip()]
            reqs = reqs.filter(Requisicao.status.in_(statuses))
        else:
            reqs = reqs.filter(Requisicao.status.in_(["pending", "updated"]))
        if limit: reqs = reqs.limit(limit=limit)
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
            obs=obs,
            criado_por_supervisor_id=supervisor_id
        )
        
        socketio.emit("new_request")
        return jsonify("Requisição criada"), 201

    @safe_route
    def update(self, token_data):
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
            obs=bd.get("obs", req.obs),
            alterado_por_usuario_id=token_data.get("id")
        )

        socketio.emit("new_request")
        return jsonify("Requisição alterada"), 200
        
    @safe_route
    def delete(self):
        bd = request.get_json(silent=True) or request.args
        id = bd.get("id")

        req = Requisicao.query.filter(Requisicao.id == id).first()
        if not req: return jsonify("RequisiÃ§Ã£o nÃ£o encontrada"), 404

        requisicao_id = req.id
        History.query.filter(History.requisicao_id == requisicao_id).delete(synchronize_session=False)
        Timeline.query.filter(Timeline.requisicao_id == requisicao_id).delete(synchronize_session=False)
        db.session.delete(req)
        db.session.commit()

        socketio.emit("new_history")
        socketio.emit("new_request")
        return jsonify({
            "message": "RequisiÃ§Ã£o excluÃ­da",
            "requisicao_id": requisicao_id
        }), 200

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
        latest_history = (
            db.session.query(
                History.requisicao_id,
                func.max(History.id).label("id")
            )
            .group_by(History.requisicao_id)
            .subquery()
        )

        hists = (
            db.session.query(
                History.id,
                History.requisicao_id,
                History.created_at.label("abertura"),
                History.ended_at.label("fechamento"),
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
            .join(latest_history, History.id == latest_history.c.id)
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
    def create(self, token_data):
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

        hist = History.query.filter(History.requisicao_id == requisicao_id).order_by(History.id.desc()).first()
        if not hist:
            hist = History(
                requisicao_id=requisicao_id,
                created_at=created_at,
            )
            db.session.add(hist)

        hist.reserva_id = reserva_id
        hist.ausente_id = ausente_id
        hist.cc = cc_id
        hist.status = status
        hist.ended_at = ended_at
        hist.supervisor_id = supervisor_id
        hist.motivo = motivo
        hist.obs = obs
        
        req.status = status
        req.reserva_id = reserva_id
        db.session.commit()
        
        TimelineService().create_event(
            req= req,
            status= status,
            tipo = "Aprovado" if status == "approved" else "Reprovado, posto sem cobertura.",
            obs= obs,
            alterado_por_usuario_id=token_data.get("id")
        )

        socketio.emit("new_history")
        return jsonify("Sucesso"), 201

    @safe_route
    def update(self, token_data):
        bd = request.get_json()
        id = bd.get("id")

        hist = History.query.filter(History.id == id).first()
        if not hist: return jsonify("Histórico não encontrado"), 404

        req = Requisicao.query.filter(Requisicao.id == hist.requisicao_id).first()
        if not req:
            req = Requisicao(
                id=hist.requisicao_id,
                reserva_id=hist.reserva_id,
                ausente_id=hist.ausente_id,
                cc=hist.cc,
                supervisor_id=hist.supervisor_id,
                warning=False,
                motivo=hist.motivo,
                obs=hist.obs,
                created_at=hist.created_at,
                status="updated"
            )
            db.session.add(req)

        if "reserva_id" in bd:
            hist.reserva_id = bd.get("reserva_id")
            req.reserva_id = bd.get("reserva_id")
        if "centro_id" in bd:
            hist.cc = bd.get("centro_id")
            req.cc = bd.get("centro_id")
        if "ausente_id" in bd:
            hist.ausente_id = bd.get("ausente_id")
            req.ausente_id = bd.get("ausente_id")
        if "supervisor_id" in bd:
            hist.supervisor_id = bd.get("supervisor_id")
            req.supervisor_id = bd.get("supervisor_id")
        if "motivo" in bd:
            hist.motivo = bd.get("motivo")
            req.motivo = bd.get("motivo")
        if "obs" in bd:
            hist.obs = str(bd.get("obs")).strip().upper()
            req.obs = hist.obs

        hist.status = "pending"
        req.status = "updated"

        db.session.commit()

        TimelineService().create_event(
            req=req,
            status="updated",
            tipo="Alteração do histórico",
            obs=bd.get("obs", req.obs),
            alterado_por_usuario_id=token_data.get("id")
        )

        socketio.emit("new_history")
        socketio.emit("new_request")
        return jsonify("Histórico alterado"), 200

    @safe_route
    def delete(self):
        bd = request.get_json(silent=True) or request.args
        id = bd.get("id")

        hist = History.query.filter(History.id == id).first()
        if not hist: return jsonify("HistÃ³rico nÃ£o encontrado"), 404

        requisicao_id = hist.requisicao_id
        req = Requisicao.query.filter(Requisicao.id == requisicao_id).first()

        History.query.filter(History.requisicao_id == requisicao_id).delete(synchronize_session=False)
        Timeline.query.filter(Timeline.requisicao_id == requisicao_id).delete(synchronize_session=False)
        if req: db.session.delete(req)
        db.session.commit()

        socketio.emit("new_history")
        socketio.emit("new_request")
        return jsonify({
            "message": "HistÃ³rico e requisiÃ§Ã£o excluÃ­dos",
            "history_id": id,
            "requisicao_id": requisicao_id
        }), 200

class TimelineService:
    def create_event(
        self,
        req,
        status,
        tipo,
        obs=None,
        criado_por_supervisor_id=None,
        alterado_por_usuario_id=None,
    ):
        db.session.add(
            Timeline(
                requisicao_id=req.id,
                reserva_id=req.reserva_id,
                ausente_id=req.ausente_id,
                cc=req.cc,
                supervisor_id=req.supervisor_id,
                criado_por_supervisor_id=criado_por_supervisor_id,
                alterado_por_usuario_id=alterado_por_usuario_id,
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
        Criador = aliased(Supervisors)
        Alterador = aliased(Users)

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
                Criador.nome.label("criado_por"),
                Alterador.nome.label("alterado_por"),
                Timeline.motivo,
                Timeline.obs,
            )
            .select_from(Timeline)
            .join(Ausente, Ausente.id == Timeline.ausente_id)
            .outerjoin(Reserva, Reserva.id == Timeline.reserva_id)
            .join(CostCenters, CostCenters.id == Timeline.cc)
            .join(Supervisors, Supervisors.id == Timeline.supervisor_id)
            .outerjoin(Criador, Criador.id == Timeline.criado_por_supervisor_id)
            .outerjoin(Alterador, Alterador.id == Timeline.alterado_por_usuario_id)
            .order_by(Timeline.created_at.desc())
        )

        if requisicao_id: query = query.filter(Timeline.requisicao_id == requisicao_id)
        timelines = query.all()
        return jsonify([t._asdict() for t in timelines]), 200
