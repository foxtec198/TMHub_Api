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

        response = {"abertas": 0, "historico": [], "multas": [], "meter": {'total': 0, 'cobertas': 0, 'sem_cobertura': 0}}
        response["abertas"] = Requisicao.query.filter(Requisicao.created_at.between(init, end)).count()

        Ausente = aliased(Employees)
        Reserva = aliased(Employees)
        hists = (
            db.session.query(
                History.created_at,
                Ausente.nome.label("ausente"),
                case(
                    (History.reserva_id == 0, "SEM INFORMAÇÃO"), else_=Reserva.nome
                ).label("reserva"),
                History.motivo,
                History.obs,
                Supervisors.nome.label("supervisor"),
                CostCenters.local.label("local"),
                CostCenters.departamento.label("dpto"),
                History.status,
                Cargos.multa
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
        response["historico"] = [h._asdict() for h in hists]
        
        return jsonify(response), 200
