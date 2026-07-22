# Models
from models.centros_de_custo import CostCenters, db
from models.rp_requisicao import Requisicao
from models.rp_timeline import Timeline
from models.supervisores import Supervisors
from models.colaboradores import Employees
from models.rp_historico import History
from models.cargos import Cargos
from models.usuarios import Users
from models.reservas_tecnicas import Floaters
from models.situacoes import Situations

# Utils
from datetime import date, datetime as dt, timedelta
from dateutils import relativedelta
from flask import jsonify, request, send_file
from utils.socket import socketio
from calendar import monthrange
from sqlalchemy import and_, case, func, or_
from utils.check_field import check_field
from utils.safe_route import safe_route
from sqlalchemy.orm import aliased
from io import BytesIO
from openpyxl import Workbook, load_workbook
from zoneinfo import ZoneInfo


def _emit_kds_update(action, request_id=None, status=None):
    """Notify TV dashboards without exposing requisition data over the socket."""
    socketio.emit("kds_update", {
        "action": action,
        "request_id": request_id,
        "status": status,
        "emitted_at": dt.now(ZoneInfo("America/Sao_Paulo")).isoformat(),
    })

class RequestService:
    """Owns requisition validation, date ranges, spreadsheet I/O and queue queries."""
    REASONS = {"AFASTAMENTO", "ATESTADO", "DECLARAÇÃO", "POSTO VAGO", "REMANEJAMENTO", "INJUSTIFICADA", "OUTROS"}

    @staticmethod
    def _parse_datetime(value):
        """Normalize browser ISO timestamps to a naive Sao Paulo database value."""
        if not value:
            return dt.now()
        if isinstance(value, dt):
            return value
        parsed = dt.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo:
            parsed = parsed.astimezone(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)
        return parsed

    @staticmethod
    def _spreadsheet_datetime(value):
        """Accept Excel or textual dates while preserving the current submission time."""
        now = dt.now()
        if isinstance(value, dt):
            parsed = value
        elif isinstance(value, date):
            parsed = dt.combine(value, now.time())
        else:
            raw = str(value or "").strip()
            parsed = None
            for date_format in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    parsed = dt.strptime(raw, date_format)
                    break
                except ValueError:
                    continue
            if parsed is None:
                raise ValueError("data inválida; use dd/mm/aaaa")
        return parsed.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)

    @safe_route
    def read(self):
        bd = request.args
        
        limit = bd.get("limit", None)
        id = bd.get("id", None)
        status = bd.get("status")

        Ausente = aliased(Employees)
        Reserva = aliased(Employees)
        active_statuses = ["pending", "updated"]
        request_days = (
            db.session.query(
                Requisicao.ausente_id.label("ausente_id"),
                Requisicao.cc.label("cc"),
                Requisicao.motivo.label("motivo"),
                func.count(func.distinct(func.date(Requisicao.created_at))).label("dias"),
            )
            .filter(Requisicao.status.in_(active_statuses))
            .group_by(Requisicao.ausente_id, Requisicao.cc, Requisicao.motivo)
            .subquery()
        )

        reqs = (
            db.session.query(
                Requisicao.id,
                Requisicao.reserva_id,
                Requisicao.created_at.label("data"),
                request_days.c.dias,
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
            .join(request_days, and_(
                request_days.c.ausente_id == Requisicao.ausente_id,
                request_days.c.cc == Requisicao.cc,
                request_days.c.motivo == Requisicao.motivo,
            ))
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

    @safe_route
    def kds(self):
        """Return every open requisition and only decisions finalized today."""
        Ausente = aliased(Employees)
        Reserva = aliased(Employees)
        latest_history = (
            db.session.query(
                History.requisicao_id,
                func.max(History.id).label("history_id"),
            )
            .group_by(History.requisicao_id)
            .subquery()
        )
        first_timeline = (
            db.session.query(
                Timeline.requisicao_id,
                func.min(Timeline.created_at).label("opened_at"),
            )
            .group_by(Timeline.requisicao_id)
            .subquery()
        )
        sao_paulo = ZoneInfo("America/Sao_Paulo")
        today = dt.now(sao_paulo).date()
        day_start = dt.combine(today, dt.min.time())
        day_end = dt.combine(today, dt.max.time())

        rows = (
            db.session.query(
                Requisicao.id,
                Requisicao.created_at.label("abertura"),
                first_timeline.c.opened_at.label("aberta_em"),
                Requisicao.status,
                Requisicao.motivo,
                Requisicao.obs,
                Requisicao.warning,
                Ausente.nome.label("ausente"),
                Ausente.matricula.label("ausente_matricula"),
                case(
                    (Requisicao.reserva_id == 0, "SEM COBERTURA"),
                    else_=Reserva.nome,
                ).label("reserva"),
                Reserva.matricula.label("reserva_matricula"),
                CostCenters.local.label("contrato"),
                CostCenters.departamento.label("departamento"),
                Supervisors.nome.label("supervisor"),
                History.ended_at.label("decidida_em"),
            )
            .select_from(Requisicao)
            .join(Ausente, Ausente.id == Requisicao.ausente_id)
            .outerjoin(Reserva, Reserva.id == Requisicao.reserva_id)
            .join(CostCenters, CostCenters.id == Requisicao.cc)
            .join(Supervisors, Supervisors.id == Requisicao.supervisor_id)
            .outerjoin(first_timeline, first_timeline.c.requisicao_id == Requisicao.id)
            .outerjoin(latest_history, latest_history.c.requisicao_id == Requisicao.id)
            .outerjoin(History, History.id == latest_history.c.history_id)
            .filter(or_(
                Requisicao.status.in_(["pending", "updated"]),
                and_(
                    Requisicao.status.in_(["approved", "reproved"]),
                    History.ended_at.between(day_start, day_end),
                ),
            ))
            .all()
        )

        def local_iso(value):
            return value.replace(tzinfo=sao_paulo).isoformat() if value else None

        return jsonify({
            "servidor_em": dt.now(sao_paulo).isoformat(),
            "requisicoes": [{
                **row._asdict(),
                "abertura": local_iso(row.abertura),
                "aberta_em": local_iso(row.aberta_em or row.abertura),
                "decidida_em": local_iso(row.decidida_em),
            } for row in rows],
        }), 200

    def create(self):
        bd = request.get_json()

        supervisor_id = bd.get("supervisor_id")
        reserva_id = bd.get("reserva_id")
        ausente_id = bd.get("ausente_id")
        advertencia = str(bd.get("advertencia"))
        motivo = bd.get("motivo")
        data = bd.get("data")
        obs = bd.get("obs")
        status = "pending"

        ok, error = check_field(Supervisor=supervisor_id, Ausente=ausente_id, Motivo=motivo)

        if not ok:
            return jsonify(error), 400
        adv = True if advertencia and advertencia.lower() == "aplicado" else False
        created_at = self._parse_datetime(data)
        absent_employee = db.session.get(Employees, ausente_id)
        if not absent_employee:
            return jsonify("Colaborador ausente não encontrado."), 404
        if not absent_employee.centro_id:
            return jsonify("O colaborador ausente não possui um local cadastrado."), 400
        centro_id = absent_employee.centro_id

        if reserva_id not in (None, 0):
            reservation = Floaters.query.filter_by(employee_id=reserva_id).first()
            if not reservation:
                return jsonify("A pessoa selecionada não pertence às reservas técnicas."), 400
            day_start = created_at.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = created_at.replace(hour=23, minute=59, second=59, microsecond=999999)
            conflicting_request = Requisicao.query.filter(
                Requisicao.reserva_id == reserva_id,
                Requisicao.created_at.between(day_start, day_end),
                Requisicao.status.in_(["pending", "updated", "approved"]),
            ).first()
            if conflicting_request:
                return jsonify("Esta reserva está indisponível na data informada."), 409

        new_rq = Requisicao(
            reserva_id=reserva_id,
            ausente_id=ausente_id,
            cc=centro_id,
            supervisor_id=supervisor_id,
            warning=adv,
            motivo=motivo,
            created_at=created_at,
            status=status
        )

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
        _emit_kds_update("created", new_rq.id, new_rq.status)
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
        if "data" in bd: req.created_at = self._parse_datetime(bd.get("data"))
        req.status = "updated"
        db.session.commit()

        TimelineService().create_event(
            req=req,
            status="updated",
            tipo="Alteração de Dados",
            obs=bd.get("obs", req.obs),
            alterado_por_usuario_id=token_data.get("id")
        )

        socketio.emit("new_request")
        _emit_kds_update("updated", req.id, req.status)
        return jsonify("Requisição alterada"), 200

    @safe_route
    def export(self):
        """Export only the operational queue, keeping approved/reproved items in history."""
        Ausente = aliased(Employees)
        Reserva = aliased(Employees)
        request_days = (
            db.session.query(
                Requisicao.ausente_id.label("ausente_id"),
                Requisicao.cc.label("cc"),
                Requisicao.motivo.label("motivo"),
                func.count(func.distinct(func.date(Requisicao.created_at))).label("dias"),
            )
            .filter(Requisicao.status.in_(["pending", "updated"]))
            .group_by(Requisicao.ausente_id, Requisicao.cc, Requisicao.motivo)
            .subquery()
        )
        rows = (
            db.session.query(
                Requisicao.id,
                Requisicao.created_at.label("data"),
                request_days.c.dias,
                Requisicao.status,
                Requisicao.motivo,
                Ausente.nome.label("ausente"),
                case((Requisicao.reserva_id == 0, "SEM COBERTURA"), else_=Reserva.nome).label("reserva"),
                CostCenters.local,
                CostCenters.departamento,
                Supervisors.nome.label("supervisor"),
            )
            .select_from(Requisicao)
            .join(request_days, and_(
                request_days.c.ausente_id == Requisicao.ausente_id,
                request_days.c.cc == Requisicao.cc,
                request_days.c.motivo == Requisicao.motivo,
            ))
            .join(Ausente, Ausente.id == Requisicao.ausente_id)
            .outerjoin(Reserva, Reserva.id == Requisicao.reserva_id)
            .join(CostCenters, CostCenters.id == Requisicao.cc)
            .join(Supervisors, Supervisors.id == Requisicao.supervisor_id)
            .filter(Requisicao.status.in_(["pending", "updated"]))
            .order_by(Requisicao.created_at.desc())
            .all()
        )

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Requisicoes"
        headers = ["id", "data", "dias", "status", "motivo", "ausente", "reserva", "local", "departamento", "supervisor"]
        worksheet.append(headers)
        for row in rows:
            values = row._asdict()
            worksheet.append([values.get(header) for header in headers])
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = f"A1:J{max(len(rows) + 1, 1)}"
        for column, width in {"A": 8, "B": 20, "C": 8, "D": 14, "E": 22, "F": 32, "G": 32, "H": 40, "I": 16, "J": 28}.items():
            worksheet.column_dimensions[column].width = width

        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return send_file(output, as_attachment=True, download_name="requisicoes_abertas.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    @safe_route
    def download_import_template(self):
        """Generate the canonical import sheet plus read-only ID reference tabs."""
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Requisicoes"
        headers = ["supervisor_id", "reserva_id", "centro_id", "ausente_id", "motivo", "data", "advertencia", "obs"]
        worksheet.append(headers)
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = "A1:H1"
        for column, width in {"A": 16, "B": 14, "C": 14, "D": 14, "E": 22, "F": 16, "G": 18, "H": 36}.items():
            worksheet.column_dimensions[column].width = width

        instructions = workbook.create_sheet("Instrucoes")
        instructions.append(["Campo", "Regra"])
        instructions.append(["supervisor_id", "Obrigatório; consulte a aba Supervisores"])
        instructions.append(["reserva_id", "Obrigatório; consulte a aba Reservas ou use 0 para SEM COBERTURA"])
        instructions.append(["centro_id", "Obrigatório; consulte a aba Centros"])
        instructions.append(["ausente_id", "Obrigatório; consulte a aba Colaboradores"])
        instructions.append(["motivo", "AFASTAMENTO, ATESTADO, DECLARAÇÃO, POSTO VAGO, REMANEJAMENTO, INJUSTIFICADA ou OUTROS"])
        instructions.append(["data", "Obrigatório; somente hoje ou amanhã, no formato dd/mm/aaaa"])
        instructions.append(["advertencia", "Opcional; use APLICADO ou NÃO APLICADO"])
        instructions.append(["obs", "Opcional"])

        reference_sheets = [
            ("Supervisores", ["id", "nome"], db.session.query(Supervisors.id, Supervisors.nome).order_by(Supervisors.nome).all()),
            ("Reservas", ["id", "matricula", "nome"], db.session.query(Employees.id, Employees.matricula, Employees.nome).select_from(Floaters).join(Employees, Employees.id == Floaters.employee_id).order_by(Employees.nome).all()),
            ("Colaboradores", ["id", "matricula", "nome"], db.session.query(Employees.id, Employees.matricula, Employees.nome).order_by(Employees.nome).all()),
            ("Centros", ["id", "local", "departamento"], db.session.query(CostCenters.id, CostCenters.local, CostCenters.departamento).order_by(CostCenters.id).all()),
        ]
        for title, sheet_headers, rows in reference_sheets:
            sheet = workbook.create_sheet(title)
            sheet.append(sheet_headers)
            for row in rows:
                sheet.append(list(row))
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions

        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return send_file(output, as_attachment=True, download_name="modelo_importacao_requisicoes.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    @safe_route
    def import_requests(self):
        """Validate every spreadsheet row before committing requests and timelines atomically."""
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename.lower().endswith(".xlsx"):
            return jsonify("Envie uma planilha no formato .xlsx."), 400

        try:
            workbook = load_workbook(uploaded.stream, read_only=True, data_only=True)
            worksheet = workbook["Requisicoes"] if "Requisicoes" in workbook.sheetnames else workbook.active
            rows = worksheet.iter_rows(values_only=True)
            headers = [str(value or "").strip().lower() for value in next(rows)]
        except (StopIteration, ValueError, OSError):
            return jsonify("Não foi possível ler a planilha."), 400

        required = ["supervisor_id", "reserva_id", "centro_id", "ausente_id", "motivo", "data"]
        if any(field not in headers for field in required):
            return jsonify({"message": "Planilha fora do padrão.", "errors": [f"Colunas obrigatórias: {', '.join(required)}."]}), 400

        indexes = {header: position for position, header in enumerate(headers)}
        # Cache valid foreign keys once to avoid one database round trip per spreadsheet row.
        supervisor_ids = {row[0] for row in db.session.query(Supervisors.id).all()}
        employee_ids = {row[0] for row in db.session.query(Employees.id).all()}
        reservation_ids = {row[0] for row in db.session.query(Floaters.employee_id).all()}
        center_ids = {row[0] for row in db.session.query(CostCenters.id).all()}
        today = dt.now().date()
        allowed_dates = {today, today + timedelta(days=1)}
        created = []
        errors = []

        for row_number, row in enumerate(rows, start=2):
            if not any(value is not None and str(value).strip() for value in row):
                continue
            if row_number > 1001:
                errors.append("A planilha pode conter no máximo 1000 requisições.")
                break

            def value(field, default=None):
                position = indexes.get(field)
                return row[position] if position is not None and position < len(row) else default

            try:
                supervisor_id = int(value("supervisor_id"))
                reserva_id = int(value("reserva_id"))
                centro_id = int(value("centro_id"))
                ausente_id = int(value("ausente_id"))
                motivo = str(value("motivo") or "").strip().upper()
                created_at = self._spreadsheet_datetime(value("data"))
            except (TypeError, ValueError) as error:
                errors.append(f"Linha {row_number}: {error}.")
                continue

            row_errors = []
            if supervisor_id not in supervisor_ids: row_errors.append("supervisor_id não encontrado")
            if reserva_id != 0 and reserva_id not in reservation_ids: row_errors.append("reserva_id não pertence às reservas técnicas")
            if centro_id not in center_ids: row_errors.append("centro_id não encontrado")
            if ausente_id not in employee_ids: row_errors.append("ausente_id não encontrado")
            if motivo not in self.REASONS: row_errors.append("motivo inválido")
            if created_at.date() not in allowed_dates: row_errors.append("a data deve ser hoje ou amanhã")
            if row_errors:
                errors.append(f"Linha {row_number}: {', '.join(row_errors)}.")
                continue

            warning_value = str(value("advertencia") or "").strip().upper()
            obs = str(value("obs") or "").strip().upper() or None
            requisition = Requisicao(
                reserva_id=reserva_id,
                ausente_id=ausente_id,
                cc=centro_id,
                supervisor_id=supervisor_id,
                warning=warning_value == "APLICADO",
                motivo=motivo,
                obs=obs,
                created_at=created_at,
                status="pending",
            )
            db.session.add(requisition)
            created.append(requisition)

        # Any invalid row cancels the complete batch; partial operational queues are unsafe.
        if errors:
            db.session.rollback()
            return jsonify({"message": "A importação foi cancelada; nenhuma requisição foi criada.", "errors": errors}), 400
        if not created:
            return jsonify("A planilha não contém requisições para importar."), 400

        # Flush IDs first so each request and its initial timeline event share one transaction.
        db.session.flush()
        for requisition in created:
            db.session.add(Timeline(
                requisicao_id=requisition.id,
                reserva_id=requisition.reserva_id,
                ausente_id=requisition.ausente_id,
                cc=requisition.cc,
                supervisor_id=requisition.supervisor_id,
                criado_por_supervisor_id=requisition.supervisor_id,
                status="pending",
                tipo="Criação da requisição por planilha",
                motivo=requisition.motivo,
                obs=requisition.obs,
            ))
        db.session.commit()
        socketio.emit("new_request")
        _emit_kds_update("imported")
        return jsonify({"message": f"{len(created)} requisições importadas com sucesso.", "total": len(created)}), 201

    def daily_reservations(self):
        """Split technical reserves by availability for one requested calendar day."""
        value = request.args.get("data")
        try:
            day = dt.strptime(value, "%Y-%m-%d") if value else dt.now()
        except ValueError:
            return jsonify("Data inválida."), 400
        init = day.replace(hour=0, minute=0, second=0, microsecond=0)
        end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Durações antigas não bloqueiam datas posteriores; somente o dia de abertura conta.
        used_ids = {
            row[0] for row in db.session.query(Requisicao.reserva_id)
            .filter(
                Requisicao.created_at.between(init, end),
                Requisicao.reserva_id > 0,
                Requisicao.status.in_(["pending", "updated", "approved"]),
            ).distinct().all()
        }
        # Último contrato considera todo uso registrado até o fim do dia consultado.
        # A janela mantém somente a requisição mais recente de cada reserva.
        last_usage = (
            db.session.query(
                Requisicao.reserva_id.label("reserva_id"),
                CostCenters.local.label("ultimo_contrato"),
                func.row_number().over(
                    partition_by=Requisicao.reserva_id,
                    order_by=Requisicao.created_at.desc(),
                ).label("ordem"),
            )
            .join(CostCenters, CostCenters.id == Requisicao.cc)
            .filter(
                Requisicao.created_at <= end,
                Requisicao.reserva_id > 0,
                Requisicao.status.in_(["pending", "updated", "approved"]),
            )
            .subquery()
        )

        reservations = (
            db.session.query(
                Employees.id,
                Employees.nome,
                Employees.matricula,
                Cargos.nome.label("cargo"),
                Situations.tipo.label("situacao"),
                last_usage.c.ultimo_contrato,
            )
            .select_from(Floaters)
            .join(Employees, Employees.id == Floaters.employee_id)
            .join(Cargos, Cargos.id == Employees.cargo)
            .join(Situations, Situations.id == Employees.situacao)
            .outerjoin(last_usage, and_(
                last_usage.c.reserva_id == Employees.id,
                last_usage.c.ordem == 1,
            ))
            .order_by(Employees.nome)
            .all()
        )
        response = [{**row._asdict(), "usada": row.id in used_ids} for row in reservations]
        return jsonify({
            "data": init.strftime("%Y-%m-%d"),
            "usadas": [row for row in response if row["usada"]],
            "disponiveis": [row for row in response if not row["usada"]],
        }), 200
        
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
        _emit_kds_update("deleted", requisicao_id)
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
        absence_days = (
            db.session.query(
                History.ausente_id.label("ausente_id"),
                History.cc.label("cc"),
                History.motivo.label("motivo"),
                func.count(func.distinct(func.date(History.created_at))).label("dias"),
            )
            .join(latest_history, History.id == latest_history.c.id)
            .filter(History.created_at.between(init, end))
            .group_by(History.ausente_id, History.cc, History.motivo)
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
                absence_days.c.dias,
                Supervisors.nome.label("supervisor"),
                CostCenters.local.label("local"),
                CostCenters.departamento.label("dpto"),
                History.status,
                Cargos.multa,
                
            )
            .select_from(History)
            .join(latest_history, History.id == latest_history.c.id)
            .join(absence_days, and_(
                absence_days.c.ausente_id == History.ausente_id,
                absence_days.c.cc == History.cc,
                absence_days.c.motivo == History.motivo,
            ))
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
        _emit_kds_update("decided", requisicao_id, status)
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
        _emit_kds_update("reopened", req.id, req.status)
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
        _emit_kds_update("deleted", requisicao_id)
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
