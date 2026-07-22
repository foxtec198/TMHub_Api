from datetime import datetime as dt, timedelta
from zoneinfo import ZoneInfo

from flask import jsonify, request
from sqlalchemy import case, or_
from sqlalchemy.orm import aliased

from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from models.controle_faltas import AbsenceControl
from models.rp_requisicao import Requisicao
from models.supervisores import Supervisors
from models.usuarios import Users
from utils.db import db
from utils.filial_scope import apply_cost_center_scope, can_access_cost_center, is_admin
from utils.safe_route import safe_route
from utils.socket import socketio


SAO_PAULO = ZoneInfo("America/Sao_Paulo")
JUSTIFIED_REASON_TERMS = ("ATESTADO", "AFASTAMENTO", "DECLARAÇÃO", "DECLARAÃ‡ÃƒO")


class AbsenceControlService:
    @staticmethod
    def _requires_document_deadline(reason):
        normalized = str(reason or "").strip().upper()
        return "ATESTADO" in normalized or "DECLARA" in normalized

    @staticmethod
    def _is_historical(value):
        if not value:
            return False
        local_value = value.astimezone(SAO_PAULO) if value.tzinfo else value.replace(tzinfo=SAO_PAULO)
        return local_value.date() < dt.now(SAO_PAULO).date()

    @staticmethod
    def _mark_historical_as_treated(absence):
        now = dt.now(SAO_PAULO)
        absence.status = "tratada"
        absence.prazo_atestado = None
        absence.tratado_por_usuario_id = None
        absence.tratado_em = now
        absence.automatizado_em = now

    @staticmethod
    def _can_manage(token_data):
        if is_admin(token_data):
            return True
        user = db.session.get(Users, (token_data or {}).get("id"))
        return bool(user and user.gerencia_faltas)

    @staticmethod
    def _initial_classification(reason):
        normalized = str(reason or "").strip().upper()
        if normalized == "INJUSTIFICADA":
            return "injustificada"
        if any(term in normalized for term in JUSTIFIED_REASON_TERMS):
            return "justificada"
        return "em_analise"

    @staticmethod
    def _deadline(req):
        if not AbsenceControlService._requires_document_deadline(req.motivo):
            return None
        opened = req.opened_at or dt.now(SAO_PAULO)
        if opened.tzinfo is None:
            opened = opened.replace(tzinfo=SAO_PAULO)
        scheduled = req.created_at
        if scheduled and scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=SAO_PAULO)
        reference = max(opened, scheduled) if scheduled else opened
        return reference + timedelta(hours=48)

    @classmethod
    def ensure_for_request(cls, req):
        with db.session.no_autoflush:
            absence = AbsenceControl.query.filter_by(requisicao_id=req.id).first()
            employee = db.session.get(Employees, req.ausente_id)
        is_new = absence is None
        if not absence:
            absence = AbsenceControl(requisicao_id=req.id)
            db.session.add(absence)
        absence.colaborador_id = employee.id if employee else None
        absence.colaborador_nome = employee.nome if employee else "Colaborador não encontrado"
        absence.colaborador_matricula = employee.matricula if employee else None
        absence.centro_custo_id = req.cc
        absence.supervisor_id = req.supervisor_id
        absence.motivo = req.motivo
        absence.data_falta = req.created_at
        if is_new and req.obs:
            absence.observacao = req.obs
        if absence.status != "tratada":
            absence.classificacao = cls._initial_classification(req.motivo)
            if is_new and cls._is_historical(req.created_at):
                cls._mark_historical_as_treated(absence)
            else:
                absence.prazo_atestado = cls._deadline(req)
        return absence

    @staticmethod
    def _expire_certificates():
        now = dt.now(SAO_PAULO)
        expired = AbsenceControl.query.filter(
            AbsenceControl.status == "pendente",
            or_(
                db.func.upper(AbsenceControl.motivo).like("%ATESTADO%"),
                db.func.upper(AbsenceControl.motivo).like("%DECLARA%"),
            ),
            AbsenceControl.prazo_atestado.isnot(None),
            AbsenceControl.prazo_atestado <= now,
            AbsenceControl.classificacao != "injustificada",
        ).all()
        for absence in expired:
            absence.classificacao = "injustificada"
            absence.automatizado_em = now
        if expired:
            db.session.commit()

    @safe_route
    def read(self, token_data):
        if not self._can_manage(token_data):
            return jsonify("Você não possui acesso ao Controle de Faltas."), 403
        self._expire_certificates()
        Tratador = aliased(Users)
        query = (
            db.session.query(
                AbsenceControl.id,
                AbsenceControl.requisicao_id,
                AbsenceControl.data_falta,
                AbsenceControl.motivo,
                AbsenceControl.prazo_atestado,
                AbsenceControl.classificacao,
                AbsenceControl.status,
                AbsenceControl.observacao,
                AbsenceControl.tratado_em,
                AbsenceControl.automatizado_em,
                db.func.coalesce(Employees.nome, AbsenceControl.colaborador_nome).label("colaborador"),
                db.func.coalesce(Employees.matricula, AbsenceControl.colaborador_matricula).label("matricula"),
                CostCenters.local.label("contrato"),
                CostCenters.departamento,
                Supervisors.nome.label("supervisor"),
                Tratador.nome.label("tratado_por"),
                Requisicao.status.label("status_requisicao"),
            )
            .select_from(AbsenceControl)
            .outerjoin(Employees, Employees.id == AbsenceControl.colaborador_id)
            .join(CostCenters, CostCenters.id == AbsenceControl.centro_custo_id)
            .join(Supervisors, Supervisors.id == AbsenceControl.supervisor_id)
            .join(Requisicao, Requisicao.id == AbsenceControl.requisicao_id)
            .outerjoin(Tratador, Tratador.id == AbsenceControl.tratado_por_usuario_id)
            .order_by(
                case((AbsenceControl.status == "pendente", 0), else_=1),
                AbsenceControl.prazo_atestado.asc().nullslast(),
                AbsenceControl.data_falta.desc(),
            )
        )
        rows = apply_cost_center_scope(query, AbsenceControl.centro_custo_id, token_data).all()
        return jsonify([row._asdict() for row in rows]), 200

    @safe_route
    def update(self, token_data):
        if not self._can_manage(token_data):
            return jsonify("Você não possui acesso ao Controle de Faltas."), 403
        body = request.get_json(silent=True) or {}
        absence = db.session.get(AbsenceControl, body.get("id"))
        if not absence:
            return jsonify("Registro de falta não encontrado."), 404
        if not can_access_cost_center(token_data, absence.centro_custo_id):
            return jsonify("Você não possui acesso à filial deste registro."), 403

        if "motivo" in body:
            reason = str(body.get("motivo") or "").strip().upper()
            if not reason:
                return jsonify("Informe o motivo."), 400
            absence.motivo = reason
            req = db.session.get(Requisicao, absence.requisicao_id)
            if req:
                req.motivo = reason
            if absence.status != "tratada":
                absence.classificacao = self._initial_classification(reason)
                if req:
                    absence.prazo_atestado = self._deadline(req)
        if "data_falta" in body:
            try:
                value = dt.fromisoformat(str(body.get("data_falta")).replace("Z", "+00:00"))
            except ValueError:
                return jsonify("Data da falta inválida."), 400
            absence.data_falta = value
            req = db.session.get(Requisicao, absence.requisicao_id)
            if req:
                req.created_at = value
                if absence.status != "tratada" and self._is_historical(value):
                    absence.classificacao = self._initial_classification(absence.motivo)
                    self._mark_historical_as_treated(absence)
                elif absence.status != "tratada":
                    absence.prazo_atestado = self._deadline(req)
        if "observacao" in body:
            absence.observacao = str(body.get("observacao") or "").strip() or None

        if body.get("status") == "tratada":
            classification = str(body.get("classificacao") or "").lower()
            if classification not in {"justificada", "injustificada"}:
                return jsonify("Informe se a falta foi justificada ou injustificada."), 400
            absence.status = "tratada"
            absence.classificacao = classification
            absence.tratado_por_usuario_id = token_data.get("id")
            absence.tratado_em = dt.now(SAO_PAULO)
        elif body.get("status") == "pendente":
            absence.status = "pendente"
            absence.tratado_por_usuario_id = None
            absence.tratado_em = None

        db.session.commit()
        socketio.emit("absence_control_update", {"id": absence.id})
        return jsonify("Registro de falta atualizado."), 200
