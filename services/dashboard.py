from flask import jsonify, request as rq
from utils.safe_route import safe_route
from datetime import datetime as dt
from dateutils import relativedelta
from sqlalchemy import case, func, extract
from sqlalchemy.orm import aliased

from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from models.reposicoes import Requisicao, History, db
from models.supervisores import Supervisors
from models.cargos import Cargos

class DashboardService:
    @safe_route
    def get_repos(self):
        bd = rq.get_json()

        init = bd.get("init", None)
        end = bd.get("end", None)

        if init and end: init = dt.now().strptime(init, "%d/%m/%Y"); end = dt.now().strptime(end, "%d/%m/%Y")
        else: init = dt.now().replace(day=1); end = init + relativedelta(months=1)

        response = {"counts": {}, "historico": [], "multas": [], "meter": {'total': 0, 'cobertas': 0, 'sem_cobertura': 0}}
        response.get("counts")["realizadas"] = History.query.filter(History.created_at.between(init, end)).count()
        response.get("counts")["aprovadas"] = History.query.filter(History.created_at.between(init, end), History.status == "approve").count()
        response.get("counts")["reprovadas"] = History.query.filter(History.created_at.between(init, end), History.status == "reproved").count()
        response.get("counts")["abertas"] = Requisicao.query.count()

        Ausente = aliased(Employees)
        Reserva = aliased(Employees)
        hists = (
            db.session.query(
                History.created_at,
                Ausente.nome.label("ausente"),
                case(
                    (History.reserva_id == 0, "SEM COBERTURA"), else_=Reserva.nome
                ).label("reserva"),
                History.motivo,
                History.obs,
                Supervisors.nome.label("supervisor"),
                CostCenters.local.label("local"),
                CostCenters.departamento.label("dpto")
            )
            .select_from(History)
            .join(Ausente, Ausente.id == History.ausente_id)
            .outerjoin(Reserva, Reserva.id == History.reserva_id)
            .join(CostCenters, CostCenters.id == History.cc)
            .join(Supervisors, Supervisors.id == History.supervisor_id)
            .filter(History.created_at.between(init, end))
            .order_by(History.created_at.desc())
            .all()
        )
        response["historico"] = [h._asdict() for h in hists]

        multas = (
            db.session.query(
                extract("day", History.created_at).label("dia"),
                func.sum(Cargos.multa).label("total_multas"),
            )
            .select_from(History)
            .join(Employees, Employees.id == History.reserva_id)
            .join(Cargos, Cargos.id == Employees.cargo)
            .filter(History.created_at.between(init, end))
            .group_by(extract("day", History.created_at))
            .order_by(extract("day", History.created_at))
            .all()
        )
        response["multas"] = [m._asdict() for m in multas]

        key_list = (
            db.session.query(
                extract("day", History.created_at).label("dia"),
                func.count(History.ausente_id).label("ausentes"),
                func.sum(case((History.reserva_id != 0, 1), else_=0)).label("reservas"),
            )
            .filter(History.created_at.between(init, end))
            .group_by(extract("day", History.created_at))
            .order_by(extract("day", History.created_at))
            .all()
        )
        response["repos"] = [k._asdict() for k in key_list]

        meter = (
            db.session.query(
                func.count(History.id).label("total"),
                func.sum(case((History.reserva_id != 0, 1), else_=0)).label("cobertas"),
                func.sum(case((History.reserva_id == 0, 1), else_=0)).label(
                    "sem_cobertura"
                ),
            )
            .filter(History.created_at.between(init, end))
            .first()
        )
        if meter: response["meter"] = meter._asdict()

        return jsonify(response), 200
