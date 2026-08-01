from flask import jsonify, request as rq
from utils.safe_route import safe_route
from utils.check_field import check_field
from datetime import date, datetime as dt, time
import re
from sqlalchemy import String, cast
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from zoneinfo import ZoneInfo

from models.colaboradores import Employees
from models.cargos import Cargos
from models.centros_de_custo import CostCenters
from models.admissao import InterviewHistory, Vacancy, VacancyCandidateHistory, VacancyEvent, WorkSchedule, db
from models.supervisores import Supervisors
from models.usuarios import Users
from utils.business_time import business_hours_between
from utils.filial_scope import apply_cost_center_scope, can_access_cost_center, can_access_supervisor

STATUS_VALIDOS = ("aberta", "entrevista", "certidao", "aso", "unico", "concluido")
RESULTADOS_CANDIDATO = ("desistiu", "reprovado", "aprovado", "outro")
TIMEZONE = ZoneInfo("America/Sao_Paulo")

class VacancyService:
    """Centraliza cadastro, transições, histórico e indicadores das vagas."""
    def _parse_date(self, value):
        """Normaliza datas do JSON sem carregar horário ou conversão de fuso."""
        if not value: return None
        if isinstance(value, dt): return value.date()
        if isinstance(value, date): return value
        return date.fromisoformat(str(value)[:10])

    def _start_datetime(self, value, schedule_description):
        """Combina o dia informado com o primeiro horário encontrado na jornada."""
        start_date = self._parse_date(value)
        match = re.search(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)", schedule_description or "")
        if not match:
            raise ValueError("O horário de trabalho da vaga não possui um horário inicial válido")
        return dt.combine(start_date, time(int(match.group(1)), int(match.group(2))), tzinfo=TIMEZONE)

    def _parse_datetime(self, value):
        """Converte valores ISO para o fuso operacional de São Paulo."""
        if isinstance(value, dt):
            parsed = value
        else:
            parsed = dt.fromisoformat(str(value or "").replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=TIMEZONE)
        return parsed.astimezone(TIMEZONE)

    def _authenticated_user(self, token_data):
        """Resolve o usuário autenticado usado na auditoria das transições."""
        user_id = token_data.get("id") if token_data else None
        return db.session.get(Users, user_id) if user_id else None

    def _lookup_employee(self, colaborador_id):
        """Carrega o colaborador e os dados profissionais derivados pela vaga."""
        return (
            db.session.query(
                Employees.id,
                Employees.matricula,
                Employees.nome,
                Employees.carga_horaria,
                Cargos.nome.label("funcao"),
                CostCenters.id.label("centro_id"),
                CostCenters.departamento,
                CostCenters.local.label("centro_custo"),
            )
            .select_from(Employees)
            .join(Cargos, Cargos.id == Employees.cargo)
            .join(CostCenters, CostCenters.id == Employees.centro_id)
            .filter(Employees.id == colaborador_id)
            .first()
        )

    @staticmethod
    def _vacancy_center_id(vacancy):
        if vacancy.centro_custo_id:
            return vacancy.centro_custo_id
        return db.session.query(Employees.centro_id).filter(
            Employees.id == vacancy.colaborador_id
        ).scalar()

    def _can_access_vacancy(self, token_data, vacancy):
        center_id = self._vacancy_center_id(vacancy)
        return center_id is not None and can_access_cost_center(token_data, center_id)

    def _normalize_schedule(self, value):
        """Cria uma representação estável para pesquisar e deduplicar jornadas."""
        description = re.sub(r"\s+", " ", str(value or "").strip())
        description = re.sub(r"\s*-\s*", " - ", description).upper()
        return description, description

    def _resolve_schedule(self, value):
        """Reutiliza uma jornada existente ou cria uma nova de forma concorrente segura."""
        description, normalized = self._normalize_schedule(value)
        if not description: return None
        if len(description) > 100: raise ValueError("O horário de trabalho deve ter no máximo 100 caracteres")

        schedule = WorkSchedule.query.filter_by(descricao_normalizada=normalized).first()
        if schedule: return schedule

        try:
            with db.session.begin_nested():
                schedule = WorkSchedule(descricao=description, descricao_normalizada=normalized)
                db.session.add(schedule)
                db.session.flush()
        except IntegrityError:
            # Outra requisição pode ter criado o mesmo horário entre a busca e o insert.
            schedule = WorkSchedule.query.filter_by(descricao_normalizada=normalized).first()
        return schedule

    @safe_route
    def search(self, token_data):
        """Busca curta usada pelos seletores legados da área de admissões."""
        query = (rq.args.get("q") or "").strip()
        if len(query) < 2: return jsonify([]), 200

        termo = f"%{query}%"
        matches_query = (
            db.session.query(
                Employees.id,
                Employees.matricula,
                Employees.nome,
                Employees.carga_horaria,
                Cargos.nome.label("funcao"),
                CostCenters.id.label("centro_id"),
                CostCenters.departamento,
                CostCenters.local.label("centro_custo"),
            )
            .select_from(Employees)
            .join(Cargos, Cargos.id == Employees.cargo)
            .join(CostCenters, CostCenters.id == Employees.centro_id)
            .filter(db.or_(
                cast(Employees.matricula, String).ilike(termo),
                Employees.nome.ilike(termo),
            ))
            .order_by(Employees.nome)
        )
        matches = apply_cost_center_scope(
            matches_query, Employees.centro_id, token_data
        ).limit(6).all()
        return jsonify([m._asdict() for m in matches]), 200

    def search_schedules(self):
        """Pesquisa jornadas já cadastradas para o autocomplete da vaga."""
        query = (rq.args.get("q") or "").strip()
        schedules = WorkSchedule.query
        if query:
            _, normalized = self._normalize_schedule(query)
            schedules = schedules.filter(WorkSchedule.descricao_normalizada.ilike(f"%{normalized}%"))
        schedules = schedules.order_by(WorkSchedule.descricao).limit(20).all()
        return jsonify([{"id": item.id, "descricao": item.descricao} for item in schedules]), 200

    @safe_route
    def read_interview_history(self, token_data):
        """Entrega o histórico enriquecido com colaborador, contrato e vínculo do candidato."""
        search = (rq.args.get("search") or "").strip()
        status = (rq.args.get("status") or "").strip()
        limit = min(max(int(rq.args.get("limit", 1000)), 1), 2000)

        colaborador_saida = aliased(Employees)
        candidato = aliased(Employees)
        responsavel = aliased(Users)
        cargo = aliased(Cargos)
        supervisor = aliased(Supervisors)
        query = (
            db.session.query(
                InterviewHistory,
                colaborador_saida.matricula.label("colaborador_saida_matricula"),
                colaborador_saida.nome.label("colaborador_saida_nome"),
                CostCenters.local.label("contrato"),
                CostCenters.departamento.label("departamento"),
                candidato.nome.label("candidato_nome_vinculado"),
                responsavel.nome.label("responsavel"),
                cargo.nome.label("funcao_vinculada"),
                supervisor.nome.label("supervisor_vinculado"),
            )
            .join(colaborador_saida, colaborador_saida.id == InterviewHistory.colaborador_saida_id)
            .join(CostCenters, CostCenters.id == InterviewHistory.centro_custo_id)
            .outerjoin(candidato, candidato.id == InterviewHistory.candidato_colaborador_id)
            .outerjoin(responsavel, responsavel.id == InterviewHistory.responsavel_usuario_id)
            .outerjoin(cargo, cargo.id == InterviewHistory.cargo_id)
            .outerjoin(supervisor, supervisor.id == InterviewHistory.supervisor_id)
        )
        query = apply_cost_center_scope(
            query, InterviewHistory.centro_custo_id, token_data
        )
        if search:
            term = f"%{search}%"
            query = query.filter(db.or_(
                InterviewHistory.candidato_nome.ilike(term),
                colaborador_saida.nome.ilike(term),
                cast(colaborador_saida.matricula, String).ilike(term),
                InterviewHistory.funcao.ilike(term),
                cargo.nome.ilike(term),
                CostCenters.local.ilike(term),
                InterviewHistory.substituicao.ilike(term),
                InterviewHistory.supervisor.ilike(term),
                supervisor.nome.ilike(term),
            ))
        if status: query = query.filter(InterviewHistory.status == status)

        rows = query.order_by(
            InterviewHistory.entrevista_data.desc().nullslast(),
            InterviewHistory.inicio_data.desc().nullslast(),
            InterviewHistory.id.desc(),
        ).limit(limit).all()
        result = []
        for result_row in rows:
            row = result_row.InterviewHistory
            item = row.to_dict()
            item.update({
                "colaborador_saida_matricula": result_row.colaborador_saida_matricula,
                "colaborador_saida_nome": result_row.colaborador_saida_nome,
                "contrato": result_row.contrato,
                "departamento": result_row.departamento,
                "candidato_nome": result_row.candidato_nome_vinculado or row.candidato_nome,
                "candidato_vinculado": row.candidato_colaborador_id is not None,
                "responsavel": result_row.responsavel,
                "funcao": result_row.funcao_vinculada or row.funcao,
                "supervisor": result_row.supervisor_vinculado or row.supervisor,
            })
            item["entrevista_data"] = row.entrevista_data.isoformat() if row.entrevista_data else None
            item["inicio_data"] = row.inicio_data.isoformat() if row.inicio_data else None
            result.append(item)
        return jsonify(result), 200

    @safe_route
    def admission_dashboard(self, token_data):
        """Calcula SLA, séries mensais e recortes executivos no período solicitado."""
        today = dt.now(TIMEZONE).date()
        end_date = self._parse_date(rq.args.get("fim") or today.isoformat())
        start_raw = rq.args.get("inicio")
        if start_raw:
            start_date = self._parse_date(start_raw)
        else:
            month_index = today.year * 12 + today.month - 1 - 5
            start_date = date(month_index // 12, month_index % 12 + 1, 1)
        if start_date > end_date:
            return jsonify("O início do período deve ser anterior ao fim"), 400

        action_target = min(max(int(rq.args.get("meta_acao_horas", 24)), 1), 720)
        close_target = min(max(int(rq.args.get("meta_conclusao_horas", 120)), 1), 2160)
        start_at = dt.combine(start_date, time.min, tzinfo=TIMEZONE)
        end_at = dt.combine(end_date, time.max, tzinfo=TIMEZONE)

        # O painel reúne o histórico importado e as vagas alimentadas no TMHub em uma série única.
        records = []
        responsavel_historico = aliased(Users)
        historical_query = (
            db.session.query(
                InterviewHistory,
                CostCenters.departamento,
                CostCenters.local.label("contrato"),
                responsavel_historico.nome.label("responsavel"),
            )
            .join(CostCenters, CostCenters.id == InterviewHistory.centro_custo_id)
            .outerjoin(responsavel_historico, responsavel_historico.id == InterviewHistory.responsavel_usuario_id)
            .filter(InterviewHistory.aviso_em.between(start_at, end_at))
        )
        historical_rows = apply_cost_center_scope(
            historical_query, InterviewHistory.centro_custo_id, token_data
        ).all()
        for row in historical_rows:
            item = row.InterviewHistory
            records.append({
                "id": f"historico-{item.id}",
                "status": "concluido",
                "aviso_em": item.aviso_em,
                "primeira_acao_em": item.primeira_acao_em,
                "entrevista_em": item.entrevista_em_sla,
                "concluido_em": item.concluido_em,
                "departamento": row.departamento,
                "contrato": row.contrato,
                "responsavel": row.responsavel or "Rafael Nogara",
                "colaborador_saida": None,
                "candidato": item.candidato_nome,
                "tentativas": 1 if item.candidato_nome else 0,
                "data_saida": None,
                "data_saida_prevista": False,
            })

        responsavel_vaga = aliased(Users)
        colaborador_contratado = aliased(Employees)
        vacancy_query = (
            db.session.query(
                Vacancy,
                Employees.nome.label("colaborador_saida"),
                colaborador_contratado.nome.label("colaborador_contratado"),
                CostCenters.departamento,
                CostCenters.local.label("contrato"),
                responsavel_vaga.nome.label("responsavel"),
            )
            .outerjoin(Employees, Employees.id == Vacancy.colaborador_id)
            .join(
                CostCenters,
                CostCenters.id == db.func.coalesce(Vacancy.centro_custo_id, Employees.centro_id),
            )
            .outerjoin(
                colaborador_contratado, cast(colaborador_contratado.matricula, String)
                == Vacancy.colaborador_entrada_matricula,
            )
            .outerjoin(responsavel_vaga, responsavel_vaga.id == Vacancy.responsavel_usuario_id)
            .filter(
                Vacancy.aviso_em.between(start_at, end_at),
                Vacancy.tipo == "substituicao",
            )
        )
        vacancy_rows = apply_cost_center_scope(
            vacancy_query, CostCenters.id, token_data
        ).all()
        # Eventos preservam quem realizou a primeira ação e em qual instante ela ocorreu.
        vacancy_ids = [row.Vacancy.id for row in vacancy_rows]
        candidate_attempts = {}
        if vacancy_ids:
            candidate_attempts = dict(
                db.session.query(
                    VacancyCandidateHistory.vaga_id,
                    db.func.count(VacancyCandidateHistory.id),
                )
                .filter(VacancyCandidateHistory.vaga_id.in_(vacancy_ids))
                .group_by(VacancyCandidateHistory.vaga_id)
                .all()
            )
        events_by_vacancy = {vacancy_id: [] for vacancy_id in vacancy_ids}
        if vacancy_ids:
            event_rows = (
                db.session.query(VacancyEvent, Users.nome.label("usuario_nome"))
                .outerjoin(Users, Users.id == VacancyEvent.usuario_id)
                .filter(VacancyEvent.vaga_id.in_(vacancy_ids))
                .order_by(VacancyEvent.ocorrido_em, VacancyEvent.id)
                .all()
            )
            for event_row in event_rows:
                events_by_vacancy[event_row.VacancyEvent.vaga_id].append(event_row)

        for row in vacancy_rows:
            vacancy = row.Vacancy
            actions = [event for event in events_by_vacancy.get(vacancy.id, []) if event.VacancyEvent.status != "aberta"]
            first_action = actions[0] if actions else None
            finalized_attempts = candidate_attempts.get(vacancy.id, 0)
            if vacancy.status == "concluido":
                attempts = max(finalized_attempts, 1 if vacancy.colaborador_entrada else 0)
            else:
                attempts = finalized_attempts + (1 if vacancy.colaborador_entrada else 0)
            records.append({
                "id": f"vaga-{vacancy.id}",
                "status": vacancy.status,
                "aviso_em": vacancy.aviso_em,
                "primeira_acao_em": first_action.VacancyEvent.ocorrido_em if first_action else None,
                "entrevista_em": vacancy.entrevista_data,
                "concluido_em": vacancy.concluido_em,
                "departamento": row.departamento,
                "contrato": row.contrato,
                "responsavel": row.responsavel or (first_action.usuario_nome if first_action else "Rafael Nogara"),
                "colaborador_saida": row.colaborador_saida,
                "tipo": vacancy.tipo,
                "candidato": (
                    row.colaborador_contratado
                    if vacancy.status == "concluido" and row.colaborador_contratado
                    else "Colaborador contratado ainda não encontrado"
                    if vacancy.status == "concluido"
                    else vacancy.colaborador_entrada
                ),
                "candidato_matricula": vacancy.colaborador_entrada_matricula,
                "tentativas": attempts,
                "data_saida": vacancy.data_saida,
                # A presença da data identifica a vaga planejada durante todo o seu ciclo.
                # Assim ela não passa a distorcer o SLA quando o dia da saída chegar.
                "data_saida_prevista": vacancy.data_saida is not None,
            })

        # As opções são montadas antes do recorte para o painel não perder escolhas
        # quando um filtro estiver ativo.
        filter_options = {
            "departamentos": sorted(
                {str(record["departamento"]) for record in records if record["departamento"] is not None},
                key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value),
            ),
            "status": sorted({record["status"] for record in records if record["status"]}),
            "contratos": sorted({record["contrato"] for record in records if record["contrato"]}),
            "responsaveis": sorted({record["responsavel"] for record in records if record["responsavel"]}),
            "colaboradores": sorted({
                value
                for record in records
                for value in (record.get("colaborador_saida"), record.get("candidato"))
                if value
            }),
        }
        department_filter = rq.args.get("departamento")
        status_filter = rq.args.get("status")
        contract_filter = rq.args.get("contrato")
        responsible_filter = rq.args.get("responsavel")
        collaborator_filter = rq.args.get("colaborador")
        records = [
            record for record in records
            if (not department_filter or str(record["departamento"]) == department_filter)
            and (not status_filter or record["status"] == status_filter)
            and (not contract_filter or record["contrato"] == contract_filter)
            and (not responsible_filter or record["responsavel"] == responsible_filter)
            and (
                not collaborator_filter
                or record.get("colaborador_saida") == collaborator_filter
                or record.get("candidato") == collaborator_filter
            )
        ]

        # Tempos em aberto usam o instante atual; tempos concluídos usam datas persistidas.
        now = dt.now(TIMEZONE)
        for record in records:
            if record["data_saida_prevista"]:
                record["sla_acao_horas"] = None
                record["sla_conclusao_horas"] = None
                record["sla_acao_decorrido_horas"] = None
                record["acao_no_prazo"] = False
                record["conclusao_no_prazo"] = False
                record["sla_estourado"] = False
                continue

            notice = record["aviso_em"]
            action = record["primeira_acao_em"]
            closed = record["concluido_em"]
            record["sla_acao_horas"] = business_hours_between(notice, action) if action else None
            record["sla_conclusao_horas"] = business_hours_between(notice, closed) if closed else None
            elapsed = business_hours_between(notice, action or now)
            record["sla_acao_decorrido_horas"] = elapsed
            record["acao_no_prazo"] = record["sla_acao_horas"] is not None and record["sla_acao_horas"] <= action_target
            record["conclusao_no_prazo"] = record["sla_conclusao_horas"] is not None and record["sla_conclusao_horas"] <= close_target
            record["sla_estourado"] = action is None and elapsed > action_target

        action_values = [record["sla_acao_horas"] for record in records if record["sla_acao_horas"] is not None]
        close_values = [record["sla_conclusao_horas"] for record in records if record["sla_conclusao_horas"] is not None]
        evaluated = [record for record in records if record["sla_acao_horas"] is not None]
        compliant = [
            record for record in evaluated
            if record["acao_no_prazo"] and (record["sla_conclusao_horas"] is None or record["conclusao_no_prazo"])
        ]

        # Meses sem movimento também são emitidos para o gráfico não criar lacunas visuais.
        month_keys = []
        cursor_year, cursor_month = start_date.year, start_date.month
        while (cursor_year, cursor_month) <= (end_date.year, end_date.month):
            month_keys.append(f"{cursor_year:04d}-{cursor_month:02d}")
            cursor_month += 1
            if cursor_month == 13:
                cursor_year += 1
                cursor_month = 1
        monthly = {key: {"mes": key, "avisadas": 0, "concluidas": 0, "acao": [], "conclusao": []} for key in month_keys}
        for record in records:
            notice_key = record["aviso_em"].strftime("%Y-%m")
            if notice_key in monthly:
                monthly[notice_key]["avisadas"] += 1
                if record["sla_acao_horas"] is not None:
                    monthly[notice_key]["acao"].append(record["sla_acao_horas"])
                if record["sla_conclusao_horas"] is not None:
                    monthly[notice_key]["conclusao"].append(record["sla_conclusao_horas"] / 24)
            if record["concluido_em"]:
                close_key = record["concluido_em"].strftime("%Y-%m")
                if close_key in monthly:
                    monthly[close_key]["concluidas"] += 1
        monthly_result = []
        for item in monthly.values():
            monthly_result.append({
                "mes": item["mes"],
                "avisadas": item["avisadas"],
                "concluidas": item["concluidas"],
                "sla_acao_horas": round(sum(item["acao"]) / len(item["acao"]), 1) if item["acao"] else None,
                "sla_conclusao_dias": round(sum(item["conclusao"]) / len(item["conclusao"]), 1) if item["conclusao"] else None,
            })

        # Agregação por departamento usa somente registros avaliáveis no denominador do SLA.
        departments = {}
        for record in records:
            key = str(record["departamento"] if record["departamento"] is not None else "Sem DPTO")
            bucket = departments.setdefault(key, {
                "departamento": key,
                "total": 0,
                "data_prevista": 0,
                "acao": [],
                "conclusao": [],
                "no_prazo": 0,
            })
            bucket["total"] += 1
            if record["data_saida_prevista"]:
                bucket["data_prevista"] += 1
            if record["sla_acao_horas"] is not None:
                bucket["acao"].append(record["sla_acao_horas"])
                if record["acao_no_prazo"] and (record["sla_conclusao_horas"] is None or record["conclusao_no_prazo"]):
                    bucket["no_prazo"] += 1
            if record["sla_conclusao_horas"] is not None:
                bucket["conclusao"].append(record["sla_conclusao_horas"] / 24)
        department_result = []
        for bucket in departments.values():
            evaluated_count = len(bucket["acao"])
            department_result.append({
                "departamento": bucket["departamento"],
                "total": bucket["total"],
                "data_prevista": bucket["data_prevista"],
                "avaliadas_sla": evaluated_count,
                "sla_acao_horas": round(sum(bucket["acao"]) / evaluated_count, 1) if evaluated_count else None,
                "sla_conclusao_dias": round(sum(bucket["conclusao"]) / len(bucket["conclusao"]), 1) if bucket["conclusao"] else None,
                "percentual_no_prazo": round(bucket["no_prazo"] * 100 / evaluated_count, 1) if evaluated_count else None,
            })
        department_result.sort(key=lambda item: (-item["total"], item["departamento"]))

        status_counts = {status: 0 for status in STATUS_VALIDOS}
        for record in records:
            if record["id"].startswith("vaga-"):
                status_counts[record["status"]] += 1

        def serialize_record(record):
            return {
                **{key: value for key, value in record.items() if not key.endswith("_em")},
                "aviso_em": record["aviso_em"].isoformat() if record["aviso_em"] else None,
                "primeira_acao_em": record["primeira_acao_em"].isoformat() if record["primeira_acao_em"] else None,
                "entrevista_em": record["entrevista_em"].isoformat() if record["entrevista_em"] else None,
                "concluido_em": record["concluido_em"].isoformat() if record["concluido_em"] else None,
                "data_saida": record["data_saida"].isoformat() if record["data_saida"] else None,
            }

        recent = sorted(records, key=lambda item: item["aviso_em"], reverse=True)[:12]
        attention = sorted(
            [
                record for record in records
                if record["id"].startswith("vaga-")
                and record["status"] != "concluido"
                and not record["data_saida_prevista"]
            ],
            key=lambda item: item["sla_acao_decorrido_horas"],
            reverse=True,
        )[:10]

        return jsonify({
            "periodo": {"inicio": start_date.isoformat(), "fim": end_date.isoformat()},
            "metas": {"acao_horas": action_target, "conclusao_horas": close_target},
            "indicadores": {
                "total_vagas": len(records),
                "vagas_em_andamento": sum(record["status"] != "concluido" for record in records),
                "vagas_concluidas": sum(record["status"] == "concluido" for record in records),
                "vagas_data_prevista": sum(record["data_saida_prevista"] for record in records),
                "vagas_avaliadas_sla": sum(not record["data_saida_prevista"] for record in records),
                "sla_acao_medio_horas": round(sum(action_values) / len(action_values), 1) if action_values else None,
                "sla_conclusao_medio_dias": round(sum(close_values) / len(close_values) / 24, 1) if close_values else None,
                "percentual_no_prazo": round(len(compliant) * 100 / len(evaluated), 1) if evaluated else None,
                "aguardando_primeira_acao": sum(
                    not record["data_saida_prevista"] and record["primeira_acao_em"] is None
                    for record in records
                ),
                "sla_estourado": sum(record["sla_estourado"] for record in records),
            },
            "mensal": monthly_result,
            "status": [{"status": key, "total": value} for key, value in status_counts.items()],
            "departamentos": department_result,
            "filtros": filter_options,
            "atencao": [serialize_record(record) for record in attention],
            "recentes": [serialize_record(record) for record in recent],
        }), 200

    @safe_route
    def read(self, token_data):
        """Lista vagas com todos os dados derivados necessários para a interface."""
        status = rq.args.get("status")
        departamento = rq.args.get("departamento")
        tipo = rq.args.get("tipo")
        order = rq.args.get("order", "desc")

        colaborador_entrada = aliased(Employees)
        recrutador = aliased(Users)
        responsavel = aliased(Users)
        query = (
            db.session.query(
                Vacancy.id,
                Vacancy.tipo,
                Vacancy.colaborador_id,
                Vacancy.centro_custo_id,
                Vacancy.supervisor_id,
                Supervisors.nome.label("supervisor"),
                Vacancy.responsavel_usuario_id,
                responsavel.nome.label("responsavel"),
                Employees.matricula,
                Employees.nome.label("colaborador"),
                CostCenters.departamento,
                CostCenters.local.label("centro_custo"),
                Cargos.nome.label("funcao"),
                Employees.carga_horaria,
                Vacancy.horario_trabalho_id,
                WorkSchedule.descricao.label("horario_trabalho"),
                Vacancy.motivo_saida,
                Vacancy.data_saida,
                Vacancy.colaborador_entrada,
                Vacancy.telefone_colaborador_entrada,
                Vacancy.colaborador_entrada_id,
                Vacancy.colaborador_entrada_matricula,
                colaborador_entrada.nome.label("colaborador_entrada_cadastrado"),
                colaborador_entrada.matricula.label("colaborador_entrada_matricula_cadastrada"),
                Vacancy.data_inicio,
                Vacancy.observacao_conclusao,
                Vacancy.concluido_por_usuario_id,
                recrutador.nome.label("concluido_por_usuario"),
                Vacancy.concluido_em,
                Vacancy.data_aviso,
                Vacancy.aviso_em,
                Vacancy.status,
                Vacancy.entrevistador,
                Vacancy.entrevista_data,
                Vacancy.created_at,
                Vacancy.updated_at,
            )
            .select_from(Vacancy)
            .outerjoin(Employees, Employees.id == Vacancy.colaborador_id)
            .outerjoin(Cargos, Cargos.id == Employees.cargo)
            .join(
                CostCenters,
                CostCenters.id == db.func.coalesce(Vacancy.centro_custo_id, Employees.centro_id),
            )
            .outerjoin(Supervisors, Supervisors.id == Vacancy.supervisor_id)
            .outerjoin(responsavel, responsavel.id == Vacancy.responsavel_usuario_id)
            .outerjoin(WorkSchedule, WorkSchedule.id == Vacancy.horario_trabalho_id)
            .outerjoin(
                colaborador_entrada,
                db.or_(
                    colaborador_entrada.id == Vacancy.colaborador_entrada_id,
                    cast(colaborador_entrada.matricula, String)
                    == Vacancy.colaborador_entrada_matricula,
                ),
            )
            .outerjoin(recrutador, recrutador.id == Vacancy.concluido_por_usuario_id)
        )
        query = apply_cost_center_scope(query, CostCenters.id, token_data)
        if status: query = query.filter(Vacancy.status == status)
        if tipo: query = query.filter(Vacancy.tipo == tipo)
        if departamento: query = query.filter(CostCenters.departamento == int(departamento))

        query = query.order_by(Vacancy.created_at.asc() if order == "asc" else Vacancy.created_at.desc())
        vagas = query.all()
        vaga_ids = [vaga.id for vaga in vagas]
        historicos_por_vaga = {vaga_id: [] for vaga_id in vaga_ids}
        if vaga_ids:
            usuario_registro = aliased(Users)
            colaborador_vinculado = aliased(Employees)
            historicos = (
                db.session.query(
                    VacancyCandidateHistory,
                    usuario_registro.nome.label("registrado_por"),
                    colaborador_vinculado.nome.label("colaborador_vinculado"),
                    colaborador_vinculado.matricula.label("colaborador_matricula"),
                )
                .outerjoin(usuario_registro, usuario_registro.id == VacancyCandidateHistory.registrado_por_usuario_id)
                .outerjoin(colaborador_vinculado, colaborador_vinculado.id == VacancyCandidateHistory.colaborador_id)
                .filter(VacancyCandidateHistory.vaga_id.in_(vaga_ids))
                .order_by(VacancyCandidateHistory.ocorrido_em.desc(), VacancyCandidateHistory.id.desc())
                .all()
            )
            for historico in historicos:
                item = historico.VacancyCandidateHistory
                historicos_por_vaga[item.vaga_id].append({
                    "id": item.id,
                    "candidato_nome": item.candidato_nome,
                    "telefone": item.telefone,
                    "resultado": item.resultado,
                    "observacao": item.observacao,
                    "colaborador_id": item.colaborador_id,
                    "colaborador_vinculado": historico.colaborador_vinculado,
                    "colaborador_matricula": historico.colaborador_matricula,
                    "registrado_por": historico.registrado_por,
                    "ocorrido_em": item.ocorrido_em.isoformat() if item.ocorrido_em else None,
                })

        resultado = []
        for vaga in vagas:
            item = vaga._asdict()
            item["historico_candidatos"] = historicos_por_vaga.get(vaga.id, [])
            resultado.append(item)
        return jsonify(resultado), 200

    @safe_route
    def create_candidate_history(self, token_data):
        """Registra um desfecho manual e libera a vaga para receber outro candidato."""
        body = rq.get_json() or {}
        vaga = db.session.get(Vacancy, body.get("vaga_id"))
        if not vaga: return jsonify("Vaga não encontrada"), 404
        if not self._can_access_vacancy(token_data, vaga):
            return jsonify("Você não possui acesso à filial desta vaga"), 403
        if vaga.status == "concluido": return jsonify("A vaga já está concluída"), 400

        resultado = (body.get("resultado") or "").strip().lower()
        if resultado not in ("desistiu", "reprovado", "outro"):
            return jsonify("Resultado de candidato inválido"), 400

        candidato_nome = (body.get("candidato_nome") or vaga.colaborador_entrada or "").strip()
        observacao = (body.get("observacao") or "").strip()
        telefone = (body.get("telefone") or vaga.telefone_colaborador_entrada or "").strip() or None
        if not candidato_nome: return jsonify("Informe o nome do candidato"), 400
        if not observacao: return jsonify("Informe a justificativa do resultado"), 400

        usuario = self._authenticated_user(token_data)
        if not usuario: return jsonify("Usuário responsável não encontrado"), 404

        db.session.add(VacancyCandidateHistory(
            vaga_id=vaga.id,
            candidato_nome=candidato_nome,
            telefone=telefone,
            resultado=resultado,
            observacao=observacao,
            registrado_por_usuario_id=usuario.id,
            ocorrido_em=dt.now(TIMEZONE),
        ))
        # A tentativa permanece no histórico e os campos livres ficam prontos para a próxima pessoa.
        vaga.colaborador_entrada = None
        vaga.telefone_colaborador_entrada = None
        vaga.updated_at = dt.now(TIMEZONE)
        db.session.commit()
        return jsonify("Resultado do candidato registrado com sucesso"), 201

    @safe_route
    def create(self, token_data):
        """Cria a vaga e seu primeiro evento de auditoria na mesma transação."""
        body = rq.get_json()
        tipo = (body.get("tipo") or "substituicao").strip().lower()
        colaborador_id = body.get("colaborador_id")
        centro_custo_id = body.get("centro_custo_id")
        supervisor_id = body.get("supervisor_id")
        colaborador_entrada = (body.get("colaborador_entrada") or "").strip() or None
        telefone_colaborador_entrada = (body.get("telefone_colaborador_entrada") or "").strip() or None
        aviso_em_raw = body.get("aviso_em") or body.get("data_aviso")
        horario_trabalho = body.get("horario_trabalho")
        motivo_saida = body.get("motivo_saida")
        data_saida_raw = body.get("data_saida")

        if tipo not in ("substituicao", "aditivo"):
            return jsonify("Tipo de vaga inválido"), 400

        required = {"aviso_em": aviso_em_raw, "horario_trabalho": horario_trabalho}
        if tipo == "aditivo":
            required["centro_custo_id"] = centro_custo_id
        else:
            required.update({
                "colaborador_id": colaborador_id,
                "supervisor_id": supervisor_id,
                "motivo_saida": motivo_saida,
            })
        ok, error = check_field(**required)
        if not ok: return jsonify(error), 400

        emp = None
        center = None
        supervisor = None
        if tipo == "aditivo":
            center = db.session.get(CostCenters, centro_custo_id)
            if not center: return jsonify("Contrato não encontrado na base"), 404
            if not can_access_cost_center(token_data, center.id):
                return jsonify("Você não possui acesso à filial deste contrato"), 403
            supervisor = db.session.get(Supervisors, center.supervisor_id) if center.supervisor_id else None
            motivo_saida = "ADITIVO CONTRATUAL"
        else:
            emp = self._lookup_employee(colaborador_id)
            if not emp: return jsonify("Colaborador não encontrado na base"), 404
            if not can_access_cost_center(token_data, emp.centro_id):
                return jsonify("Você não possui acesso à filial deste colaborador"), 403

            supervisor = db.session.get(Supervisors, supervisor_id)
            if not supervisor: return jsonify("Supervisor não encontrado na base"), 404
            if not can_access_supervisor(token_data, supervisor_id):
                return jsonify("Você não possui acesso à filial deste supervisor"), 403

        try:
            schedule = self._resolve_schedule(horario_trabalho)
        except ValueError as error:
            return jsonify(str(error)), 400

        try:
            aviso_em = self._parse_datetime(aviso_em_raw)
        except (TypeError, ValueError):
            return jsonify("Data e hora do aviso inválidas"), 400

        try:
            data_saida = self._parse_date(data_saida_raw) if tipo == "substituicao" else None
        except (TypeError, ValueError):
            return jsonify("Data de saída inválida"), 400

        created_at = dt.now(TIMEZONE)
        if aviso_em > created_at:
            return jsonify("A data do aviso deve ser anterior à criação da vaga"), 400

        recrutador = self._authenticated_user(token_data)
        if not recrutador:
            return jsonify("Usuário responsável não encontrado"), 404

        nova_vaga = Vacancy(
            tipo=tipo,
            colaborador_id=emp.id if emp else None,
            centro_custo_id=center.id if center else None,
            supervisor_id=supervisor.id if supervisor else None,
            responsavel_usuario_id=recrutador.id,
            colaborador_entrada=colaborador_entrada,
            telefone_colaborador_entrada=telefone_colaborador_entrada,
            data_aviso=aviso_em.date(),
            aviso_em=aviso_em,
            created_at=created_at,
            updated_at=created_at,
            horario_trabalho_id=schedule.id,
            motivo_saida=motivo_saida,
            data_saida=data_saida,
        )
        db.session.add(nova_vaga)
        db.session.flush()
        db.session.add(VacancyEvent(
            vaga_id=nova_vaga.id,
            status="aberta",
            usuario_id=recrutador.id,
            ocorrido_em=nova_vaga.created_at or dt.now(TIMEZONE),
        ))
        db.session.commit()
        return jsonify("Vaga cadastrada com sucesso"), 201

    @safe_route
    def update(self, token_data):
        """Atualiza dados livres e aplica as regras obrigatórias de cada transição."""
        body = rq.get_json()
        id = body.get("id")

        ok, error = check_field(id=id)
        if not ok: return jsonify(error), 400

        vaga = Vacancy.query.filter_by(id=id).first()
        if not vaga: return jsonify("Vaga não encontrada"), 404
        if not self._can_access_vacancy(token_data, vaga):
            return jsonify("Você não possui acesso à filial desta vaga"), 403

        status_anterior = vaga.status
        novo_status = body.get("status")
        if novo_status is not None and novo_status not in STATUS_VALIDOS:
            return jsonify("Status inválido"), 400

        if novo_status and novo_status != vaga.status:
            usuario_acao = self._authenticated_user(token_data)
            if not usuario_acao:
                return jsonify("Usuário responsável não encontrado"), 404

            if novo_status == "entrevista":
                entrevistador = body.get("entrevistador", vaga.entrevistador)
                entrevista_data = body.get("entrevista_data", vaga.entrevista_data)

                ok, error = check_field(entrevistador=entrevistador, entrevista_data=entrevista_data)
                if not ok: return jsonify("Informe a colaboradora responsável e a data/horário da entrevista"), 400

                vaga.entrevistador = entrevistador
                vaga.entrevista_data = entrevista_data

            if novo_status == "concluido":
                colaborador_entrada_matricula = str(body.get("colaborador_entrada_matricula") or "").strip()
                data_inicio = body.get("data_inicio")
                ok, error = check_field(
                    colaborador_entrada_matricula=colaborador_entrada_matricula,
                    data_inicio=data_inicio,
                )
                if not ok:
                    return jsonify("Informe a matrícula do colaborador que entrou e a data de início"), 400

                novo_colaborador = (
                    db.session.get(Employees, int(colaborador_entrada_matricula))
                    if colaborador_entrada_matricula.isdigit()
                    else None
                )
                if (
                    novo_colaborador
                    and novo_colaborador.centro_id
                    and not can_access_cost_center(token_data, novo_colaborador.centro_id)
                ):
                    return jsonify("Você não possui acesso à filial do colaborador informado"), 403

                horario = db.session.get(WorkSchedule, vaga.horario_trabalho_id)
                if not horario:
                    return jsonify("A vaga não possui horário de trabalho cadastrado"), 400

                try:
                    vaga.data_inicio = self._start_datetime(data_inicio, horario.descricao)
                except (TypeError, ValueError):
                    return jsonify("Data de início ou horário de trabalho inválido"), 400

                texto_entrada = (body.get("colaborador_entrada") or "").strip()
                vaga.colaborador_entrada_matricula = colaborador_entrada_matricula
                vaga.colaborador_entrada_id = novo_colaborador.id if novo_colaborador else None
                vaga.colaborador_entrada = (
                    texto_entrada
                    or (novo_colaborador.nome if novo_colaborador else vaga.colaborador_entrada)
                    or f"Matrícula {colaborador_entrada_matricula}"
                )
                vaga.observacao_conclusao = (body.get("observacao_conclusao") or "").strip() or None
                vaga.concluido_por_usuario_id = usuario_acao.id
                vaga.concluido_em = dt.now(TIMEZONE)
                db.session.add(VacancyCandidateHistory(
                    vaga_id=vaga.id,
                    candidato_nome=vaga.colaborador_entrada,
                    telefone=vaga.telefone_colaborador_entrada,
                    resultado="aprovado",
                    observacao=vaga.observacao_conclusao,
                    colaborador_id=novo_colaborador.id if novo_colaborador else None,
                    registrado_por_usuario_id=usuario_acao.id,
                    ocorrido_em=vaga.concluido_em,
                ))

            vaga.status = novo_status
            db.session.add(VacancyEvent(
                vaga_id=vaga.id,
                status=novo_status,
                usuario_id=usuario_acao.id,
                ocorrido_em=dt.now(TIMEZONE),
            ))

        if "data_aviso" in body:
            try:
                vaga.data_aviso = self._parse_date(body["data_aviso"])
            except ValueError:
                return jsonify("Data do aviso inválida"), 400

        if "aviso_em" in body:
            try:
                novo_aviso = self._parse_datetime(body["aviso_em"])
                created_at = vaga.created_at
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=TIMEZONE)
                if novo_aviso > created_at:
                    return jsonify("A data do aviso deve ser anterior à criação da vaga"), 400
                vaga.aviso_em = novo_aviso
                vaga.data_aviso = vaga.aviso_em.date()
            except (TypeError, ValueError):
                return jsonify("Data e hora do aviso inválidas"), 400

        if "horario_trabalho" in body:
            try:
                schedule = self._resolve_schedule(body["horario_trabalho"])
            except ValueError as error:
                return jsonify(str(error)), 400
            if not schedule: return jsonify("Informe o horário de trabalho"), 400
            vaga.horario_trabalho_id = schedule.id

        if "data_saida" in body:
            if vaga.tipo == "aditivo" and body["data_saida"]:
                return jsonify("Data de saída é exclusiva para vagas de substituição"), 400

            try:
                vaga.data_saida = self._parse_date(body["data_saida"])
            except (TypeError, ValueError):
                return jsonify("Data de saída inválida"), 400

        if "supervisor_id" in body:
            supervisor = db.session.get(Supervisors, body["supervisor_id"])
            if not supervisor: return jsonify("Supervisor não encontrado na base"), 404
            if not can_access_supervisor(token_data, supervisor.id):
                return jsonify("Você não possui acesso à filial deste supervisor"), 403
            vaga.supervisor_id = supervisor.id

        # Após a conclusão, o colaborador vinculado é a fonte oficial e o texto fica congelado.
        candidate_fields = ("colaborador_entrada", "telefone_colaborador_entrada")
        if status_anterior == "concluido" and any(campo in body for campo in candidate_fields):
            return jsonify("Nome e telefone do candidato não podem ser alterados após a conclusão"), 400

        campos = ("motivo_saida", "entrevistador", "entrevista_data", *candidate_fields)
        for campo in campos:
            if campo in body and not (campo == "colaborador_entrada" and novo_status == "concluido"):
                valor = body[campo]
                if campo in candidate_fields:
                    valor = (valor or "").strip() or None
                setattr(vaga, campo, valor)

        vaga.updated_at = dt.now()
        db.session.commit()
        return jsonify("Vaga atualizada com sucesso"), 200

    @safe_route
    def delete(self, token_data):
        """Remove uma vaga; os eventos são excluídos pelo cascade do banco."""
        id = rq.args.get("id")

        ok, error = check_field(id=id)
        if not ok: return jsonify(error), 400

        vaga = Vacancy.query.filter_by(id=id).first()
        if not vaga: return jsonify("Vaga não encontrada"), 404
        if not self._can_access_vacancy(token_data, vaga):
            return jsonify("Você não possui acesso à filial desta vaga"), 403

        db.session.delete(vaga)
        db.session.commit()
        return jsonify("Vaga removida com sucesso"), 200
