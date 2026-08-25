# Regras de negócio de dashboard.
# Dependências externas.
from flask import jsonify, request as rq
# Módulos internos da aplicação.
from utils.safe_route import safe_route
# Biblioteca padrão.
from datetime import datetime as dt
# Dependências externas.
from dateutils import relativedelta
from sqlalchemy import case, func, or_
from sqlalchemy.orm import aliased
# Biblioteca padrão.
from calendar import monthrange

# Módulos internos da aplicação.
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
    RESERVE_ABSENCE_NOTE = "FALTA REGISTRADA PELA INDISPONIBILIDADE DA RESERVA TÉCNICA · SEM COBERTURA"

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
                Cargos.nome.label("cargo")
            )
            .select_from(Employees)
            .join(CostCenters, CostCenters.id == Employees.centro_id)
            .join(Situations, Situations.id == Employees.situacao)
            .join(Cargos, Cargos.id == Employees.cargo)
            .outerjoin(Supervisors, Supervisors.id == CostCenters.supervisor_id)
            .outerjoin(Cities, Cities.id == CostCenters.cidade_id)
            .filter(CostCenters.departamento.notin_([0, 10, 24]))
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
        
        response = {
            "historico": [],
            "abertas_registros": [],
            "faltas_reservas": [],
        }

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
                    (
                        or_(History.reserva_id == 0, History.reserva_id.is_(None)),
                        "SEM COBERTURA",
                    ),
                    else_=Reserva.nome,
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

        # As solicitações em aberto seguem o mesmo formato do histórico. Isso
        # permite ao front aplicar um único recorte em todos os indicadores,
        # sem misturar uma contagem global aos filtros locais.
        open_query = (
            db.session.query(
                Requisicao.id,
                Ausente.nome.label("ausente"),
                case(
                    (
                        or_(Requisicao.reserva_id == 0, Requisicao.reserva_id.is_(None)),
                        "SEM COBERTURA",
                    ),
                    else_=Reserva.nome,
                ).label("reserva"),
                Supervisors.nome.label("supervisor"),
                CostCenters.local.label("local"),
                CostCenters.departamento.label("dpto"),
                Requisicao.created_at,
                Requisicao.status,
                Requisicao.motivo,
                Requisicao.obs,
                Requisicao.origem,
            )
            .select_from(Requisicao)
            .join(Ausente, Ausente.id == Requisicao.ausente_id)
            .outerjoin(Reserva, Reserva.id == Requisicao.reserva_id)
            .join(CostCenters, CostCenters.id == Requisicao.cc)
            .outerjoin(Supervisors, Supervisors.id == Requisicao.supervisor_id)
            .filter(
                Requisicao.created_at.between(init, end),
                Requisicao.status.in_(["pending", "updated"]),
            )
            .order_by(Requisicao.created_at.desc())
        )
        open_requests = apply_cost_center_scope(open_query, Requisicao.cc, token_data).all()
        response["abertas_registros"] = [item._asdict() for item in open_requests]

        # A indisponibilidade por FALTA cria uma requisição própria. Consultar
        # a requisição, em vez de somente o histórico, preserva a métrica
        # enquanto ela ainda está pendente e depois de concluída.
        reserve_absence_query = (
            db.session.query(
                Requisicao.id,
                Ausente.nome.label("ausente"),
                Supervisors.nome.label("supervisor"),
                CostCenters.local.label("local"),
                CostCenters.departamento.label("dpto"),
                Requisicao.created_at,
                Requisicao.status,
                Requisicao.motivo,
                Requisicao.obs,
            )
            .select_from(Requisicao)
            .join(Ausente, Ausente.id == Requisicao.ausente_id)
            .join(CostCenters, CostCenters.id == Requisicao.cc)
            .outerjoin(Supervisors, Supervisors.id == Requisicao.supervisor_id)
            .filter(
                Requisicao.created_at.between(init, end),
                Requisicao.obs == self.RESERVE_ABSENCE_NOTE,
            )
            .order_by(Requisicao.created_at.desc())
        )
        reserve_absences = apply_cost_center_scope(
            reserve_absence_query, Requisicao.cc, token_data
        ).all()
        response["faltas_reservas"] = [item._asdict() for item in reserve_absences]
        
        return jsonify(response), 200
