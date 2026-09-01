"""Leitura executiva do histórico já existente de Reservas Técnicas."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import jsonify, request
from sqlalchemy import func
from sqlalchemy.orm import aliased

from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from models.rp_historico import History
from models.rp_requisicao import Requisicao
from models.reservas_tecnicas import Floaters
from models.supervisores import Supervisors
from models.usuarios import Users
from utils.db import db
from utils.filial_scope import allowed_cost_center_ids
from utils.permissions import has_permission
from utils.safe_route import safe_route


SAO_PAULO = ZoneInfo("America/Sao_Paulo")
ACTIVE_REQUEST_STATUSES = ("pending", "updated")
RESERVE_ABSENCE_NOTE = "FALTA REGISTRADA PELA INDISPONIBILIDADE DA RESERVA TÉCNICA · SEM COBERTURA"


def _today():
    return datetime.now(SAO_PAULO).date()


def _selected_ids(name):
    values = set()
    for raw in request.args.getlist(name):
        for value in str(raw).split(","):
            if value.strip().isdigit():
                values.add(int(value))
    return values


class ReservationDashboardService:
    """Traduz o histórico operacional de reposições em visão de reservas.

    Não cria nem mantém uma tabela paralela: o painel consulta somente
    ``rp_historico`` e as requisições ainda abertas.
    """

    @staticmethod
    def _parse_dates(allowed_centers):
        del allowed_centers  # O escopo de filial é aplicado nas consultas abaixo.
        end = _today()
        raw_start = request.args.get("inicio")
        raw_end = request.args.get("fim")
        try:
            if raw_start:
                start = datetime.strptime(raw_start, "%Y-%m-%d").date()
            else:
                # Sem filtro explícito, a tela é sempre uma fotografia do
                # dia atual. Isso impede que requisições abertas para amanhã
                # sejam confundidas com volantes utilizadas hoje.
                start = end
            if raw_end:
                end = datetime.strptime(raw_end, "%Y-%m-%d").date()
        except ValueError:
            return None, None, "Datas inválidas. Use AAAA-MM-DD."
        if start > end:
            return None, None, "A data inicial não pode ser posterior à final."
        return start, end, None

    @staticmethod
    def _serialize(row, source):
        return {
            "id": f"{source}-{row.requisicao_id}",
            "data": row.created_at.date().isoformat(),
            "reserva_id": row.reserva_id,
            "matricula": row.reserva_matricula,
            "reserva": row.reserva_nome or "Volante não cadastrada",
            # Estes campos vêm da requisição que originou a cobertura. Eles
            # permitem identificar padrões de acionamento sem alterar o
            # histórico operacional já gravado.
            "supervisor": row.supervisor_nome or "Supervisor não identificado",
            "ausente": row.ausente_nome or "Colaboradora não identificada",
            "motivo": row.motivo or "Não informado",
            "observacao": row.observacao,
            "status": "Aprovada" if source == "historico" else "Em aberto",
            # A origem vem do cadastro atual da volante. O destino é o centro
            # gravado na requisição, que é o registro operacional histórico.
            "origem": {
                "centro_id": row.centro_origem_id,
                "departamento": row.departamento_origem,
                "nome": row.centro_origem_nome or "Origem não cadastrada",
            },
            "destino": {
                "centro_id": row.centro_destino_id,
                "departamento": row.departamento_destino,
                "nome": row.centro_destino_nome or "Destino não cadastrado",
            },
        }

    @classmethod
    def _usage_records(cls, start, end, allowed_centers):
        source_center = aliased(CostCenters)
        destination_center = aliased(CostCenters)
        absent_employee = aliased(Employees)
        supervisor_user = aliased(Users)
        latest_history = (
            db.session.query(History.requisicao_id, func.max(History.id).label("id"))
            .group_by(History.requisicao_id)
            .subquery()
        )
        start_datetime = datetime.combine(start, datetime.min.time())
        end_datetime = datetime.combine(end + timedelta(days=1), datetime.min.time())
        history_query = (
            db.session.query(
                History.requisicao_id.label("requisicao_id"),
                History.reserva_id.label("reserva_id"),
                History.created_at.label("created_at"),
                History.motivo.label("motivo"),
                History.obs.label("observacao"),
                Employees.nome.label("reserva_nome"),
                Employees.matricula.label("reserva_matricula"),
                absent_employee.nome.label("ausente_nome"),
                func.coalesce(supervisor_user.nome, Supervisors.nome).label("supervisor_nome"),
                source_center.id.label("centro_origem_id"),
                source_center.departamento.label("departamento_origem"),
                source_center.local.label("centro_origem_nome"),
                destination_center.id.label("centro_destino_id"),
                destination_center.departamento.label("departamento_destino"),
                # ``nome`` é a identificação completa do centro; ``local``
                # pode ser somente uma abreviação operacional.
                func.coalesce(destination_center.nome, destination_center.local).label("centro_destino_nome"),
            )
            .select_from(History)
            .join(latest_history, History.id == latest_history.c.id)
            .outerjoin(Employees, Employees.id == History.reserva_id)
            .outerjoin(absent_employee, absent_employee.id == History.ausente_id)
            .outerjoin(source_center, source_center.id == Employees.centro_id)
            .outerjoin(Supervisors, Supervisors.id == History.supervisor_id)
            .outerjoin(supervisor_user, supervisor_user.id == History.supervisor_usuario_id)
            .join(destination_center, destination_center.id == History.cc)
            .filter(
                History.reserva_id > 0,
                History.status == "approved",
                History.created_at >= start_datetime,
                History.created_at < end_datetime,
            )
        )
        if allowed_centers is not None:
            history_query = history_query.filter(destination_center.id.in_(allowed_centers))
        history_rows = history_query.all()
        closed_ids = {row.requisicao_id for row in history_rows}

        open_query = (
            db.session.query(
                Requisicao.id.label("requisicao_id"),
                Requisicao.reserva_id.label("reserva_id"),
                Requisicao.created_at.label("created_at"),
                Requisicao.motivo.label("motivo"),
                Requisicao.obs.label("observacao"),
                Employees.nome.label("reserva_nome"),
                Employees.matricula.label("reserva_matricula"),
                absent_employee.nome.label("ausente_nome"),
                func.coalesce(supervisor_user.nome, Supervisors.nome).label("supervisor_nome"),
                source_center.id.label("centro_origem_id"),
                source_center.departamento.label("departamento_origem"),
                source_center.local.label("centro_origem_nome"),
                destination_center.id.label("centro_destino_id"),
                destination_center.departamento.label("departamento_destino"),
                func.coalesce(destination_center.nome, destination_center.local).label("centro_destino_nome"),
            )
            .select_from(Requisicao)
            .outerjoin(Employees, Employees.id == Requisicao.reserva_id)
            .outerjoin(absent_employee, absent_employee.id == Requisicao.ausente_id)
            .outerjoin(source_center, source_center.id == Employees.centro_id)
            .outerjoin(Supervisors, Supervisors.id == Requisicao.supervisor_id)
            .outerjoin(supervisor_user, supervisor_user.id == Requisicao.supervisor_usuario_id)
            .join(destination_center, destination_center.id == Requisicao.cc)
            .filter(
                Requisicao.reserva_id > 0,
                Requisicao.status.in_(ACTIVE_REQUEST_STATUSES),
                Requisicao.created_at >= start_datetime,
                Requisicao.created_at < end_datetime,
            )
        )
        if allowed_centers is not None:
            open_query = open_query.filter(destination_center.id.in_(allowed_centers))
        open_rows = [row for row in open_query.all() if row.requisicao_id not in closed_ids]
        return [cls._serialize(row, "historico") for row in history_rows] + [
            cls._serialize(row, "aberta") for row in open_rows
        ]

    @staticmethod
    def _reserve_capacity_by_department(allowed_centers):
        """Conta a capacidade cadastrada de reservas por departamento de origem."""
        query = (
            db.session.query(
                CostCenters.departamento.label("departamento"),
                func.count(Floaters.id).label("total"),
            )
            .select_from(Floaters)
            .join(Employees, Employees.id == Floaters.employee_id)
            .join(CostCenters, CostCenters.id == Employees.centro_id)
            .group_by(CostCenters.departamento)
        )
        if allowed_centers is not None:
            query = query.filter(CostCenters.id.in_(allowed_centers))
        return {row.departamento: row.total for row in query.all()}

    @safe_route
    def read(self, token_data):
        if not has_permission(token_data, "reservas", "view"):
            return jsonify("Você não possui acesso ao Dashboard de Reservas."), 403

        allowed_centers = allowed_cost_center_ids(token_data)
        start, end, error = self._parse_dates(allowed_centers)
        if error:
            return jsonify(error), 400

        records = self._usage_records(start, end, allowed_centers)
        selected_departments = _selected_ids("departamento")
        selected_centers = _selected_ids("centro")
        if selected_departments:
            records = [row for row in records if row["destino"]["departamento"] in selected_departments]
        if selected_centers:
            records = [row for row in records if row["destino"]["centro_id"] in selected_centers]

        uses_by_day = Counter(row["data"] for row in records)
        absence_query = History.query.filter(
            History.created_at >= datetime.combine(start, datetime.min.time()),
            History.created_at < datetime.combine(end + timedelta(days=1), datetime.min.time()),
            History.obs == RESERVE_ABSENCE_NOTE,
        )
        if allowed_centers is not None:
            absence_query = absence_query.filter(History.cc.in_(allowed_centers))
        if selected_departments or selected_centers:
            centers_query = CostCenters.query
            if selected_departments:
                centers_query = centers_query.filter(CostCenters.departamento.in_(selected_departments))
            if selected_centers:
                centers_query = centers_query.filter(CostCenters.id.in_(selected_centers))
            absence_query = absence_query.filter(History.cc.in_([row.id for row in centers_query.all()]))
        absences_by_day = Counter(row.created_at.date().isoformat() for row in absence_query.all())

        days = []
        day = start
        while day <= end:
            key = day.isoformat()
            days.append({"data": key, "utilizacoes": uses_by_day[key], "ausencias": absences_by_day[key]})
            day += timedelta(days=1)

        reserve_capacity = self._reserve_capacity_by_department(allowed_centers)
        # Além da quantidade de requisições, a rota guarda as volantes
        # distintas. É esse número que pode ser comparado com a capacidade
        # de reservas cadastradas no departamento de origem.
        flows = defaultdict(lambda: {"utilizacoes": 0, "reservas": set()})
        for row in records:
            origin = row["origem"]
            destination = row["destino"]
            flow = flows[(origin["departamento"], origin["nome"], destination["departamento"], destination["nome"])]
            flow["utilizacoes"] += 1
            if row["reserva_id"]:
                flow["reservas"].add(row["reserva_id"])
        routes = [
            {
                "departamento_origem": origin_department,
                "origem": origin_name,
                "departamento_destino": destination_department,
                "destino": destination_name,
                "utilizacoes": values["utilizacoes"],
                "volantes_utilizadas": len(values["reservas"]),
                "total_reservas_origem": reserve_capacity.get(origin_department, 0),
                "em_outro_departamento": origin_department != destination_department,
            }
            for (origin_department, origin_name, destination_department, destination_name), values in flows.items()
        ]
        routes.sort(key=lambda item: (-item["utilizacoes"], str(item["origem"])))
        destination_centers = {
            row["destino"]["centro_id"]: {
                "value": row["destino"]["centro_id"],
                "label": f"DPTO. {row['destino']['departamento']} · {row['destino']['nome']}",
            }
            for row in records
            if row["destino"]["centro_id"] is not None
        }
        destination_departments = sorted({
            row["destino"]["departamento"] for row in records
            if row["destino"]["departamento"] is not None
        })
        unique_reserves = {row["reserva_id"] for row in records}
        return jsonify({
            "periodo": {"inicio": start.isoformat(), "fim": end.isoformat()},
            "resumo": {
                "utilizacoes": len(records),
                "volantes_mobilizadas": len(unique_reserves),
                "cessoes_entre_departamentos": sum(row["utilizacoes"] for row in routes if row["em_outro_departamento"]),
                "ausencias_volantes": sum(absences_by_day.values()),
                "rotas_acionadas": len(routes),
            },
            "dias": days,
            "rotas": routes,
            "registros": records,
            "filtros": {
                "departamentos": [{"value": value, "label": f"DPTO. {value}"} for value in destination_departments],
                "centros": sorted(destination_centers.values(), key=lambda item: item["label"]),
            },
            "atualizado_em": datetime.now(SAO_PAULO).isoformat(),
        })
