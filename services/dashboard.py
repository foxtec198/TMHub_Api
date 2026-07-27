from flask import jsonify, request as rq
from utils.safe_route import safe_route
from datetime import datetime as dt
from dateutils import relativedelta
from sqlalchemy import case, func, extract
from sqlalchemy.orm import aliased
from calendar import monthrange

from models.centros_de_custo import CostCenters, db
from models.colaboradores import Employees
from models.rp_historico import History
from models.rp_requisicao import Requisicao
from models.supervisores import Supervisors
from models.cargos import Cargos
from models.cidades import Cities
from models.situacoes import Situations
from utils.filial_scope import apply_cost_center_scope

class DashboardService:
    @safe_route
    def get_employees_by_department(self, token_data):
        query = (
            db.session.query(
                Employees.id,
                Employees.nome,
                Employees.matricula,
                Employees.data_admissao,
                Situations.id.label("situacao_id"),
                Situations.tipo.label("situacao"),
                CostCenters.id.label("centro_id"),
                CostCenters.local.label("centro_custo"),
                CostCenters.departamento,
                Supervisors.id.label("supervisor_id"),
                Supervisors.nome.label("supervisor"),
                Cities.id.label("cidade_id"),
                Cities.descricao.label("cidade"),
            )
            .select_from(Employees)
            .join(CostCenters, CostCenters.id == Employees.centro_id)
            .join(Situations, Situations.id == Employees.situacao)
            .outerjoin(Supervisors, Supervisors.id == CostCenters.supervisor_id)
            .outerjoin(Cities, Cities.id == CostCenters.cidade_id)
            .filter(Employees.situacao.in_([1, 8]), CostCenters.departamento.notin_([0, 10, 24]))
        )

        query = apply_cost_center_scope(query, Employees.centro_id, token_data)
        employees = query.order_by(
            CostCenters.departamento,
            CostCenters.local,
            Employees.nome,
        ).all()

        return jsonify([employee._asdict() for employee in employees]), 200

    @safe_route
    def get_repos(self, token_data):
        bd = rq.get_json()

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
        
        response = {"abertas": 0, "historico": [], "multas": [], "meter": {'total': 0, 'cobertas': 0, 'sem_cobertura': 0}}
        # Open requests follow the same status contract used by the operational request queue.
        open_requests = Requisicao.query.filter(
            Requisicao.created_at.between(init, end),
            Requisicao.status.in_(["pending", "updated"]),
        )
        response["abertas"] = apply_cost_center_scope(
            open_requests, Requisicao.cc, token_data
        ).count()

        Ausente = aliased(Employees)
        Reserva = aliased(Employees)
        # Keep one closed history row per request so dashboard totals are not inflated by legacy duplicates.
        latest_history = (
            db.session.query(
                History.requisicao_id,
                func.max(History.id).label("id"),
            )
            .group_by(History.requisicao_id)
            .subquery()
        )
        history_query = (
            db.session.query(
                History.id,
                Ausente.nome.label("ausente"),
                case(
                    (History.reserva_id == 0 or not History.reserva_id, "SEM COBERTURA"), else_=Reserva.nome
                ).label("reserva"),
                Supervisors.nome.label("supervisor"),
                CostCenters.local.label("local"),
                CostCenters.departamento.label("dpto"),
                History.created_at,
                History.status,
                Cargos.multa,
                History.motivo,
                History.obs,
            )
            .select_from(History)
            .join(latest_history, History.id == latest_history.c.id)
            .join(Ausente, Ausente.id == History.ausente_id)
            .outerjoin(Reserva, Reserva.id == History.reserva_id)
            .outerjoin(Cargos, Cargos.id == Reserva.cargo)
            .join(CostCenters, CostCenters.id == History.cc)
            .join(Supervisors, Supervisors.id == History.supervisor_id)
            .filter(
                History.created_at.between(init, end),
                History.status.in_(["approved", "reproved"]),
            )
            .order_by(History.created_at.desc())
        )
        hists = apply_cost_center_scope(
            history_query, History.cc, token_data
        ).all()
        response["historico"] = [h._asdict() for h in hists]
        
        return jsonify(response), 200
