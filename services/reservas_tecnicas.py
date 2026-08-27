# Regras de negócio de reservas técnicas.
# Biblioteca padrão.
from datetime import datetime as dt
from zoneinfo import ZoneInfo

# Dependências externas.
from flask import jsonify, request
# Módulos internos da aplicação.
from models.cargos import Cargos
from models.centros_de_custo import CostCenters
from models.controle_faltas import AbsenceControl
from models.rp_requisicao import Requisicao
from models.rp_timeline import Timeline
from models.situacoes import Situations
from utils.db import db

from models.colaboradores import Employees
from models.reservas_tecnicas import Floaters
from utils.filial_scope import apply_cost_center_scope, can_access_cost_center
from utils.safe_route import safe_route
from utils.socket import socketio


class FloaterService:
    UNAVAILABILITY_REASONS = {"FALTA", "APOIO"}
    RESERVE_ABSENCE_NOTE = "FALTA REGISTRADA PELA INDISPONIBILIDADE DA RESERVA TÉCNICA · SEM COBERTURA"
    SAO_PAULO = ZoneInfo("America/Sao_Paulo")

    @classmethod
    def _create_unjustified_absence(cls, employee, token_data):
        """Cria uma única requisição sem cobertura para a falta da reserva no dia."""
        center = db.session.get(CostCenters, employee.centro_id)
        if not center:
            return None, (jsonify("O local vinculado à reserva não foi encontrado."), 404)

        supervisor_usuario_id = center.supervisor_usuario_id
        if not supervisor_usuario_id:
            return None, (
                jsonify("Defina um usuário com role SUPERVISOR no contrato da reserva antes de registrar a falta."),
                400,
            )

        now = dt.now(cls.SAO_PAULO)
        scheduled_at = now.replace(tzinfo=None)
        day_start = scheduled_at.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = scheduled_at.replace(hour=23, minute=59, second=59, microsecond=999999)
        requisition = Requisicao.query.filter(
            Requisicao.ausente_id == employee.id,
            Requisicao.cc == employee.centro_id,
            Requisicao.motivo == "INJUSTIFICADA",
            Requisicao.obs == cls.RESERVE_ABSENCE_NOTE,
            Requisicao.created_at.between(day_start, day_end),
        ).first()
        if requisition:
            return requisition, None

        from services.controle_faltas import AbsenceControlService

        duplicate_message = AbsenceControlService.duplicate_request_message(
            employee.id,
            scheduled_at,
        )
        if duplicate_message:
            return None, (jsonify(duplicate_message), 409)

        requisition = Requisicao(
            reserva_id=0,
            ausente_id=employee.id,
            cc=employee.centro_id,
            supervisor_id=None,
            supervisor_usuario_id=supervisor_usuario_id,
            warning=False,
            origem="reserva_tecnica",
            motivo="INJUSTIFICADA",
            obs=cls.RESERVE_ABSENCE_NOTE,
            created_at=scheduled_at,
            opened_at=now,
            status="pending",
        )
        db.session.add(requisition)
        db.session.flush()

        AbsenceControlService.ensure_for_request(requisition)
        db.session.add(Timeline(
            requisicao_id=requisition.id,
            reserva_id=0,
            ausente_id=employee.id,
            cc=employee.centro_id,
            supervisor_id=None,
            supervisor_usuario_id=supervisor_usuario_id,
            criado_por_usuario_id=(token_data or {}).get("id"),
            status="pending",
            tipo="Falta criada pela indisponibilidade da reserva",
            motivo="INJUSTIFICADA",
            obs=cls.RESERVE_ABSENCE_NOTE,
        ))
        return requisition, None

    @safe_route
    def read(self, token_data):
        bd = request.args
        id = bd.get("id")
        
        rsv = (db.session.query(
            Employees.id,
            Floaters.id.label("floater_id"),
            Employees.matricula,
            Employees.nome,
            Cargos.nome.label("cargo"),
            Situations.tipo.label("situacao"),
            CostCenters.departamento.label("departamento"),
            CostCenters.local.label("centro_custo"),
            Floaters.created_at.label("data"),
            Floaters.disponivel,
            Floaters.indisponibilidade_motivo,
            Floaters.indisponivel_em,
        )
        .select_from(Floaters)
        .join(Employees, Employees.id == Floaters.employee_id)
        .join(Cargos, Cargos.id == Employees.cargo)
        .join(Situations, Situations.id == Employees.situacao)
        .join(CostCenters, CostCenters.id == Employees.centro_id))
        
        rsv = apply_cost_center_scope(rsv, Employees.centro_id, token_data)
        available_only = str(bd.get("disponivel", "")).strip().lower() in {"1", "true", "sim"}
        if available_only:
            rsv = rsv.filter(Floaters.disponivel.is_(True))
        if id:
            row = rsv.filter(Employees.id == id).first()
            return (jsonify(row._asdict()), 200) if row else (jsonify("Reserva não encontrada"), 404)
        return jsonify([f._asdict() for f in rsv]), 200

    @safe_route
    def add(self, token_data):
        bd = request.get_json()
        id = bd.get("id")

        flt = Floaters.query.filter(Floaters.employee_id == id).first()
        if flt: return jsonify("Volante já cadastrado!"), 400
        
        clb = Employees.query.filter(Employees.id == id).first()
        if not clb:
            return jsonify("Colaborador não encontrado"), 404
        if not clb.centro_id or not can_access_cost_center(token_data, clb.centro_id):
            return jsonify("Você não possui acesso à filial deste colaborador"), 403
        db.session.add(Floaters(employee_id = id))
        db.session.commit()
        return jsonify("Sucesso"), 201

    @safe_route
    def update(self, token_data):
        body = request.get_json(silent=True) or {}
        floater_id = body.get("id")
        if floater_id is None:
            return jsonify("Informe a reserva que deseja atualizar."), 400
        floater = db.session.get(Floaters, floater_id)
        if not floater:
            return jsonify("Reserva não encontrada."), 404

        employee = db.session.get(Employees, floater.employee_id)
        if not employee or not employee.centro_id or not can_access_cost_center(token_data, employee.centro_id):
            return jsonify("Você não possui acesso à filial desta reserva."), 403

        available = body.get("disponivel")
        if not isinstance(available, bool):
            return jsonify("Informe se a reserva está disponível ou indisponível."), 400

        if available:
            floater.disponivel = True
            floater.indisponibilidade_motivo = None
            floater.indisponivel_em = None
        else:
            reason = str(body.get("motivo") or "").strip().upper()
            if reason not in self.UNAVAILABILITY_REASONS:
                return jsonify("Selecione FALTA ou APOIO para justificar a indisponibilidade."), 400
            is_new_absence = floater.disponivel or floater.indisponibilidade_motivo != "FALTA"
            requisition = None
            if reason == "FALTA" and is_new_absence:
                requisition, error = self._create_unjustified_absence(employee, token_data)
                if error:
                    return error
            floater.disponivel = False
            floater.indisponibilidade_motivo = reason
            floater.indisponivel_em = dt.now()

        db.session.commit()
        if not available and reason == "FALTA":
            absence = AbsenceControl.query.filter_by(requisicao_id=requisition.id).first() if requisition else None
            socketio.emit("absence_control_update", {
                "id": absence.id if absence else None,
                "action": "created_from_floater_unavailability",
            })
            socketio.emit("new_request")
            socketio.emit("new_history")
        return jsonify({
            "id": floater.id,
            "disponivel": bool(floater.disponivel),
            "indisponibilidade_motivo": floater.indisponibilidade_motivo,
            "indisponivel_em": floater.indisponivel_em,
            "requisicao_id": requisition.id if not available and reason == "FALTA" and requisition else None,
        }), 200
    
    @safe_route
    def remove(self, token_data):
        bd = request.args
        id = bd.get("id")
        
        floater = Floaters.query.filter(Floaters.id == id).first()
        if not floater:
            return jsonify("Reserva não encontrada"), 404
        employee = db.session.get(Employees, floater.employee_id)
        if not employee or not employee.centro_id or not can_access_cost_center(token_data, employee.centro_id):
            return jsonify("Você não possui acesso à filial desta reserva"), 403
        db.session.delete(floater)
        db.session.commit()
        return jsonify("Sucesso"), 200
