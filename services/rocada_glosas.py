"""Métrica contratual de glosa do DPTO 92 (Roçada)."""
import calendar
from collections import defaultdict
from datetime import date, datetime

from flask import jsonify, request
from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from models.pt48 import Ponto48Espelho, Ponto48EspelhoImport
from models.rp_requisicao import Requisicao
from models.rescisoes import Termination
from services.ponto48 import Ponto48Service
from sqlalchemy import func
from utils.db import db
from utils.filial_scope import allowed_cost_center_ids
from utils.permissions import has_permission
from utils.safe_route import safe_route
from utils.socket import socketio
from werkzeug.utils import secure_filename


ROCADA_DEPARTMENT = 92
ROCADA_TARGET = 72
ROCADA_IMPORT_TAG = "[DPTO-92-ROCADA]"


class RocadaDisallowanceService:
    @staticmethod
    def _can_access(token_data):
        allowed_ids = allowed_cost_center_ids(token_data)
        if allowed_ids is None:
            return True
        return CostCenters.query.filter(
            CostCenters.id.in_(allowed_ids),
            CostCenters.departamento == ROCADA_DEPARTMENT,
        ).first() is not None

    @staticmethod
    def _require_access(token_data, action="view"):
        if not has_permission(token_data, "controle_glosas", action):
            return jsonify("Você não possui permissão para acessar a métrica de Roçada."), 403
        if not RocadaDisallowanceService._can_access(token_data):
            return jsonify("Você não possui acesso ao DPTO 92 (Roçada)."), 403
        return None

    @staticmethod
    def _require_dashboard_access(token_data):
        if not has_permission(token_data, "dashboard_glosas", "view"):
            return jsonify("Você não possui acesso ao Dashboard de Roçada."), 403
        if not RocadaDisallowanceService._can_access(token_data):
            return jsonify("Você não possui acesso ao DPTO 92 (Roçada)."), 403
        return None

    @staticmethod
    def _month_start(value):
        try:
            return datetime.strptime(str(value), "%Y-%m").date().replace(day=1)
        except (TypeError, ValueError):
            raise ValueError("Informe uma competência válida no formato AAAA-MM.")

    @staticmethod
    def _worked(row):
        return bool(row and row.quantidade_batidas and row.quantidade_batidas > 0)

    @classmethod
    def _historical_rows(cls):
        """O CSV é somente a memória anterior à implantação do TM Hub."""
        rows = (
            db.session.query(Ponto48Espelho)
            .join(Ponto48EspelhoImport, Ponto48EspelhoImport.id == Ponto48Espelho.importacao_id)
            .filter(Ponto48EspelhoImport.arquivo_espelho.like(f"{ROCADA_IMPORT_TAG}%"))
            .order_by(Ponto48EspelhoImport.created_at.desc(), Ponto48Espelho.id.desc())
            .all()
        )
        unique = {}
        for row in rows:
            unique.setdefault((row.nome_normalizado, row.data), row)
        grouped = defaultdict(dict)
        for (_name, row_date), row in unique.items():
            grouped[row_date][row.nome_normalizado] = row
        return grouped

    @staticmethod
    def _roster():
        rows = (
            db.session.query(
                Employees.id,
                Employees.nome,
                Employees.matricula,
                Employees.data_admissao,
                Employees.situacao,
                Termination.data_demissao,
            )
            .join(CostCenters, CostCenters.id == Employees.centro_id)
            .outerjoin(Termination, Termination.matricula == Employees.matricula)
            .filter(
                CostCenters.departamento == ROCADA_DEPARTMENT,
            )
            .order_by(Employees.nome.asc())
            .all()
        )
        roster = {}
        for row in rows:
            entry = roster.setdefault(row.id, {
                "id": row.id,
                "nome": row.nome,
                "matricula": row.matricula,
                "admissao": row.data_admissao.date() if hasattr(row.data_admissao, "date") else row.data_admissao,
                "situacao": row.situacao,
                "demissoes": [],
            })
            if row.data_demissao:
                entry["demissoes"].append(row.data_demissao)
        return roster

    @staticmethod
    def _roster_for_day(roster, day):
        active = {}
        for employee_id, employee in roster.items():
            admission = employee.get("admissao")
            if admission and admission > day:
                continue
            dismissed = any(
                dismissal < day and (not admission or dismissal >= admission)
                for dismissal in employee.get("demissoes", [])
            )
            if dismissed:
                continue
            if not employee.get("demissoes") and employee.get("situacao") != 1:
                continue
            active[employee_id] = employee
        return active

    @staticmethod
    def _requisitions_by_day():
        """Ausências e coberturas de toda a competência atual em Reposições."""
        current_month = date.today().replace(day=1)
        requests = (
            db.session.query(Requisicao)
            .join(CostCenters, CostCenters.id == Requisicao.cc)
            .filter(
                CostCenters.departamento == ROCADA_DEPARTMENT,
                func.date(Requisicao.created_at) >= current_month,
                Requisicao.status.in_(["pending", "updated", "approved"]),
            )
            .all()
        )
        reserve_ids = {item.reserva_id for item in requests if item.reserva_id and item.reserva_id > 0}
        reserve_names = {
            employee.id: {"id": employee.id, "nome": employee.nome, "matricula": employee.matricula}
            for employee in Employees.query.filter(Employees.id.in_(reserve_ids or {0})).all()
        }
        days = defaultdict(lambda: {"ausentes": set(), "coberturas": {}})
        for item in requests:
            request_day = item.created_at.date()
            if item.ausente_id:
                days[request_day]["ausentes"].add(item.ausente_id)
            # Reserva que já pertence ao quadro ativo não é somada de novo.
            if item.reserva_id and item.reserva_id > 0:
                reserve = reserve_names.get(item.reserva_id)
                if reserve:
                    days[request_day]["coberturas"][item.reserva_id] = reserve
        return days

    @classmethod
    def _day_metric(cls, day, historical, roster, requisitions):
        # O CSV representa somente competências fechadas antes do mês atual.
        # No mês vigente, inclusive em lançamentos retroativos, Reposições é a fonte oficial.
        if day < date.today().replace(day=1):
            records = historical.get(day, {})
            operational = day.weekday() < 5 and any(cls._worked(row) for row in records.values())
            if not operational:
                return {"data": day.isoformat(), "operacional": False, "fonte": "historico"}
            worked = sum(cls._worked(row) for row in records.values())
            return {
                "data": day.isoformat(), "operacional": True, "fonte": "historico",
                "trabalhados": worked,
                "faltantes": max(0, len(records) - worked),
                "coberturas": 0,
                "quadro": len(records),
            }

        if day.weekday() >= 5:
            return {"data": day.isoformat(), "operacional": False, "fonte": "reposicoes"}
        allocation = requisitions.get(day, {"ausentes": set(), "coberturas": {}})
        daily_roster = cls._roster_for_day(roster, day)
        daily_ids = set(daily_roster)
        absent_ids = allocation["ausentes"] & daily_ids
        coverage_count = len(set(allocation["coberturas"]) - daily_ids)
        roster_count = len(daily_roster)
        return {
            "data": day.isoformat(), "operacional": True, "fonte": "reposicoes",
            "trabalhados": max(0, roster_count - len(absent_ids)) + coverage_count,
            "faltantes": len(absent_ids),
            "coberturas": coverage_count,
            "quadro": roster_count,
        }

    @classmethod
    def _month_payload(cls, month, historical, roster, requisitions):
        current_month = date.today().replace(day=1)
        if month > current_month:
            return {
                "competencia": month.isoformat(), "mes": month.strftime("%m/%Y"),
                "meta": ROCADA_TARGET, "tem_dados": False, "futuro": True,
                "dias_operacionais": 0, "media_trabalhados": 0, "media_faltantes": 0,
                "media_quadro": 0, "coberturas": 0, "presencas": 0, "glosado": None,
                "situacao": "NÃO DEFINIDO AINDA", "dias": [],
            }
        month_days = [date(month.year, month.month, day) for day in range(1, calendar.monthrange(month.year, month.month)[1] + 1)]
        day_rows = [cls._day_metric(day, historical, roster, requisitions) for day in month_days]
        daily = [item for item in day_rows if item["operacional"]]
        has_data = bool(daily)
        average = round(sum(item["trabalhados"] for item in daily) / len(daily), 2) if daily else 0
        glosado = average < ROCADA_TARGET if has_data else None
        return {
            "competencia": month.isoformat(),
            "mes": month.strftime("%m/%Y"),
            "meta": ROCADA_TARGET,
            "tem_dados": has_data, "futuro": False,
            "dias_operacionais": len(daily),
            "media_trabalhados": average,
            "media_faltantes": round(sum(item["faltantes"] for item in daily) / len(daily), 2) if daily else 0,
            "media_quadro": round(sum(item["quadro"] for item in daily) / len(daily), 2) if daily else 0,
            "coberturas": sum(item["coberturas"] for item in daily),
            "presencas": sum(item["trabalhados"] for item in daily),
            "glosado": glosado,
            "situacao": "SEM DADOS" if not has_data else ("GLOSADO" if glosado else "NÃO GLOSADO"),
            "dias": day_rows,
        }

    @classmethod
    def _all_months(cls, historical, roster, requisitions):
        years = {date.today().year}
        years.update(day.year for day in historical)
        months = []
        for year in sorted(years, reverse=True):
            for month_number in range(1, 13):
                months.append(cls._month_payload(
                    date(year, month_number, 1), historical, roster, requisitions
                ))
        return months

    @classmethod
    def _detail(cls, month, historical, roster, requisitions):
        payload = cls._month_payload(month, historical, roster, requisitions)
        month_days = [date(month.year, month.month, day) for day in range(1, calendar.monthrange(month.year, month.month)[1] + 1)]
        people = {}
        cells = defaultdict(dict)

        for day in month_days:
            if month > date.today().replace(day=1):
                continue
            if day < date.today().replace(day=1):
                for normalized_name, row in historical.get(day, {}).items():
                    key = f"history:{normalized_name}"
                    people[key] = {"nome": row.nome_colaborador, "tipo": "histórico"}
                    cells[key][day] = {"trabalhou": cls._worked(row), "motivo": row.motivo}
                continue

            if day.weekday() >= 5:
                continue
            allocation = requisitions.get(day, {"ausentes": set(), "coberturas": {}})
            daily_roster = cls._roster_for_day(roster, day)
            for employee_id, employee in daily_roster.items():
                key = f"employee:{employee_id}"
                people[key] = {"nome": employee["nome"], "tipo": "quadro"}
                cells[key][day] = {
                    "trabalhou": employee_id not in allocation["ausentes"],
                    "motivo": "Ausência registrada em Reposições" if employee_id in allocation["ausentes"] else None,
                }
            for reserve_id, reserve in allocation["coberturas"].items():
                if reserve_id in daily_roster:
                    continue
                key = f"coverage:{reserve_id}"
                people[key] = {"nome": f"{reserve['nome']} (cobertura)", "tipo": "cobertura"}
                cells[key][day] = {"trabalhou": True, "motivo": "Cobertura de Reposições"}

        columns = [{
            "data": day.isoformat(), "dia": day.day,
            "operacional": next(item for item in payload["dias"] if item["data"] == day.isoformat())["operacional"],
        } for day in month_days]
        collaborators = []
        for key, person in sorted(people.items(), key=lambda item: item[1]["nome"]):
            collaborators.append({
                "nome": person["nome"], "tipo": person["tipo"],
                "dias": [{
                    "trabalhou": cells[key].get(day, {}).get("trabalhou", False),
                    "operacional": next(column for column in columns if column["data"] == day.isoformat())["operacional"],
                    "motivo": cells[key].get(day, {}).get("motivo"),
                } for day in month_days],
            })
        return {"resumo": payload, "colunas": columns, "colaboradores": collaborators}

    @safe_route
    def read(self, token_data):
        denied = self._require_access(token_data)
        if denied:
            return denied
        historical = self._historical_rows()
        roster = self._roster()
        requisitions = self._requisitions_by_day()
        return jsonify({
            "departamento": ROCADA_DEPARTMENT, "meta": ROCADA_TARGET,
            "meses": self._all_months(historical, roster, requisitions),
        })

    @safe_route
    def detail(self, token_data):
        denied = self._require_access(token_data)
        if denied:
            return denied
        try:
            month = self._month_start(request.args.get("competencia"))
        except ValueError as error:
            return jsonify(str(error)), 400
        historical = self._historical_rows()
        roster = self._roster()
        requisitions = self._requisitions_by_day()
        return jsonify(self._detail(month, historical, roster, requisitions))

    @safe_route
    def dashboard(self, token_data):
        denied = self._require_dashboard_access(token_data)
        if denied:
            return denied
        historical = self._historical_rows()
        roster = self._roster()
        requisitions = self._requisitions_by_day()
        return jsonify({
            "departamento": ROCADA_DEPARTMENT, "meta": ROCADA_TARGET,
            "meses": self._all_months(historical, roster, requisitions),
        })

    @safe_route
    def dashboard_detail(self, token_data):
        denied = self._require_dashboard_access(token_data)
        if denied:
            return denied
        try:
            month = self._month_start(request.args.get("competencia"))
        except ValueError as error:
            return jsonify(str(error)), 400
        historical = self._historical_rows()
        roster = self._roster()
        requisitions = self._requisitions_by_day()
        return jsonify(self._detail(month, historical, roster, requisitions))

    @safe_route
    def import_mirror(self, token_data):
        denied = self._require_access(token_data, "create")
        if denied:
            return denied
        upload = request.files.get("espelho")
        if not upload or not upload.filename:
            return jsonify("Selecione o CSV de espelho de ponto da Roçada."), 400

        try:
            period, records = Ponto48Service._read_journey_report(upload)
            existing = Ponto48EspelhoImport.query.filter(
                Ponto48EspelhoImport.periodo_inicio == period[0],
                Ponto48EspelhoImport.periodo_fim == period[1],
                Ponto48EspelhoImport.arquivo_espelho.like(f"{ROCADA_IMPORT_TAG}%"),
            ).all()
            if existing:
                ids = [item.id for item in existing]
                Ponto48Espelho.query.filter(Ponto48Espelho.importacao_id.in_(ids)).delete(synchronize_session=False)
                Ponto48EspelhoImport.query.filter(Ponto48EspelhoImport.id.in_(ids)).delete(synchronize_session=False)

            imported = Ponto48EspelhoImport(
                periodo_inicio=period[0], periodo_fim=period[1],
                arquivo_espelho=f"{ROCADA_IMPORT_TAG} {secure_filename(upload.filename)}",
                criado_por_usuario_id=token_data.get("id"),
            )
            db.session.add(imported)
            db.session.flush()
            lookup = Ponto48Service._employee_lookup()
            models = []
            for record in records:
                normalized_name = Ponto48Service._normalize_name(record["nome"])
                employee_id, match_status = Ponto48Service._resolve_employee(normalized_name, lookup)
                punches = [str(value or "").strip() for value in record["batidas"]]
                models.append(Ponto48Espelho(
                    importacao_id=imported.id, colaborador_id=employee_id,
                    nome_colaborador=record["nome"], nome_normalizado=normalized_name,
                    match_status=match_status, data=datetime.strptime(record["data"], "%d/%m/%Y").date(),
                    entrada_1=punches[0] or None, saida_1=punches[1] or None,
                    entrada_2=punches[2] or None, saida_2=punches[3] or None,
                    entrada_3=punches[4] or None, saida_3=punches[5] or None,
                    quantidade_batidas=sum(bool(value) for value in punches),
                    batida_impar=sum(bool(value) for value in punches) % 2 == 1,
                    credito_minutos=Ponto48Service._signed_duration_minutes(record["credito"]),
                    debito_minutos=Ponto48Service._signed_duration_minutes(record["debito"]),
                    intervalo_minutos=Ponto48Service._signed_duration_minutes(record["intervalo"]),
                    horas_normais_minutos=Ponto48Service._signed_duration_minutes(record["horas_normais"]),
                    horas_extras_1_minutos=Ponto48Service._signed_duration_minutes(record["horas_extras_1"]),
                    horas_extras_2_minutos=Ponto48Service._signed_duration_minutes(record["horas_extras_2"]),
                    adicional_noturno_minutos=Ponto48Service._signed_duration_minutes(record["adicional_noturno"]),
                    saldo_minutos=Ponto48Service._signed_duration_minutes(record["saldo"]), motivo=record["motivo"],
                ))
            db.session.add_all(models)
            db.session.commit()
            socketio.emit("disallowance_update", {"module": "rocada", "action": "import"})
            return jsonify({"message": "Espelho histórico da Roçada importado.", "registros": len(models)}), 201
        except (ValueError, UnicodeError) as error:
            db.session.rollback()
            return jsonify(str(error)), 400
        except Exception:
            db.session.rollback()
            raise
