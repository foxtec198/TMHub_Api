from datetime import date, datetime as dt
from decimal import Decimal, InvalidOperation

from flask import jsonify, request
from sqlalchemy.orm import aliased

from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from models.controle_faltas import AbsenceControl
from models.glosas import Disallowance
from models.usuarios import Users
from utils.db import db
from utils.filial_scope import apply_cost_center_scope, can_access_cost_center
from utils.permissions import has_permission
from utils.safe_route import safe_route
from utils.socket import socketio


VALID_COVERAGE = {"em_analise", "coberta", "descoberta"}
DEFAULT_DAILY_VALUE = Decimal("140.00")


def _parse_date(value, field):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        raise ValueError(f"{field} inválida.")


def _parse_decimal(value, field, default=None):
    if value in (None, "") and default is not None:
        return default
    try:
        parsed = Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} inválido.")
    if parsed <= 0:
        raise ValueError(f"{field} deve ser maior que zero.")
    return parsed.quantize(Decimal("0.01"))


class DisallowanceService:
    @staticmethod
    def _serialize(row):
        item = row.Disallowance
        return {
            "id": item.id,
            "competencia": item.competencia.isoformat(),
            "data_falta": item.data_falta.isoformat(),
            "centro_custo_id": item.centro_custo_id,
            "contrato": row.contrato,
            "departamento": row.departamento,
            "colaborador_id": item.colaborador_id,
            "colaborador": row.colaborador or item.colaborador_nome,
            "matricula": row.matricula or item.colaborador_matricula,
            "falta_id": item.falta_id,
            "requisicao_id": item.requisicao_id,
            "cobertura": item.cobertura,
            "quantidade_dias": float(item.quantidade_dias),
            "valor_diaria": float(item.valor_diaria),
            "valor_total": float(item.valor_total),
            "justificativa": item.justificativa,
            "observacao": item.observacao,
            "criado_por": row.criado_por,
            "alterado_por": row.alterado_por,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    @staticmethod
    def _query():
        Creator = aliased(Users)
        Editor = aliased(Users)
        return (
            db.session.query(
                Disallowance,
                CostCenters.local.label("contrato"),
                CostCenters.departamento.label("departamento"),
                Employees.nome.label("colaborador"),
                Employees.matricula.label("matricula"),
                Creator.nome.label("criado_por"),
                Editor.nome.label("alterado_por"),
            )
            .join(CostCenters, CostCenters.id == Disallowance.centro_custo_id)
            .outerjoin(Employees, Employees.id == Disallowance.colaborador_id)
            .outerjoin(Creator, Creator.id == Disallowance.criado_por_usuario_id)
            .outerjoin(Editor, Editor.id == Disallowance.alterado_por_usuario_id)
        )

    @safe_route
    def read(self, token_data):
        if not has_permission(token_data, "controle_glosas", "view"):
            return jsonify("Você não possui acesso ao Controle de Glosas."), 403

        query = apply_cost_center_scope(self._query(), Disallowance.centro_custo_id, token_data)
        if request.args.get("inicio"):
            try:
                query = query.filter(Disallowance.competencia >= _parse_date(request.args["inicio"], "Competência inicial"))
            except ValueError as error:
                return jsonify(str(error)), 400
        if request.args.get("fim"):
            try:
                query = query.filter(Disallowance.competencia <= _parse_date(request.args["fim"], "Competência final"))
            except ValueError as error:
                return jsonify(str(error)), 400
        rows = query.order_by(Disallowance.competencia.desc(), Disallowance.data_falta.desc()).all()
        records = [self._serialize(row) for row in rows]

        summary = {
            "total_registros": len(records),
            "dias": round(sum(item["quantidade_dias"] for item in records), 2),
            "valor_total": round(sum(item["valor_total"] for item in records), 2),
            "valor_coberto": round(sum(item["valor_total"] for item in records if item["cobertura"] == "coberta"), 2),
            "valor_descoberto": round(sum(item["valor_total"] for item in records if item["cobertura"] == "descoberta"), 2),
            "valor_em_analise": round(sum(item["valor_total"] for item in records if item["cobertura"] == "em_analise"), 2),
        }
        return jsonify({"registros": records, "resumo": summary, "valor_diaria_padrao": float(DEFAULT_DAILY_VALUE)}), 200

    def _apply(self, item, body, token_data, creating=False):
        try:
            if creating or "competencia" in body:
                competence = _parse_date(body.get("competencia"), "Competência")
                item.competencia = competence.replace(day=1)
            if creating or "data_falta" in body:
                item.data_falta = _parse_date(body.get("data_falta"), "Data da falta")
            if creating or "centro_custo_id" in body:
                center_id = int(body.get("centro_custo_id"))
                if not db.session.get(CostCenters, center_id):
                    return "Contrato não encontrado."
                if not can_access_cost_center(token_data, center_id):
                    return "Você não possui acesso à filial deste contrato."
                item.centro_custo_id = center_id
            if creating or "quantidade_dias" in body:
                item.quantidade_dias = _parse_decimal(body.get("quantidade_dias"), "Quantidade de dias", Decimal("1"))
            if creating or "valor_diaria" in body:
                item.valor_diaria = _parse_decimal(body.get("valor_diaria"), "Valor da diária", DEFAULT_DAILY_VALUE)
        except (TypeError, ValueError) as error:
            return str(error)

        if "cobertura" in body or creating:
            coverage = str(body.get("cobertura") or "em_analise").strip().lower()
            if coverage not in VALID_COVERAGE:
                return "Informe se a glosa está em análise, coberta ou descoberta."
            item.cobertura = coverage

        if "falta_id" in body:
            absence_id = body.get("falta_id") or None
            absence = db.session.get(AbsenceControl, absence_id) if absence_id else None
            if absence_id and not absence:
                return "Registro de falta não encontrado."
            if absence and not can_access_cost_center(token_data, absence.centro_custo_id):
                return "Você não possui acesso à falta informada."
            item.falta_id = absence.id if absence else None
            item.requisicao_id = absence.requisicao_id if absence else None
            if absence:
                item.colaborador_id = absence.colaborador_id
                item.colaborador_nome = absence.colaborador_nome
                item.colaborador_matricula = absence.colaborador_matricula
                item.data_falta = absence.data_falta.date()
                item.centro_custo_id = absence.centro_custo_id

        if "colaborador_id" in body and not body.get("falta_id"):
            employee_id = body.get("colaborador_id") or None
            employee = db.session.get(Employees, employee_id) if employee_id else None
            if employee_id and not employee:
                return "Colaborador não encontrado."
            item.colaborador_id = employee.id if employee else None
            item.colaborador_nome = employee.nome if employee else str(body.get("colaborador_nome") or "").strip() or None
            item.colaborador_matricula = employee.matricula if employee else str(body.get("colaborador_matricula") or "").strip() or None
        elif "colaborador_nome" in body and not item.colaborador_id:
            item.colaborador_nome = str(body.get("colaborador_nome") or "").strip() or None
            item.colaborador_matricula = str(body.get("colaborador_matricula") or "").strip() or None

        if "justificativa" in body or creating:
            item.justificativa = str(body.get("justificativa") or "").strip() or None
        if "observacao" in body or creating:
            item.observacao = str(body.get("observacao") or "").strip() or None
        item.valor_total = (Decimal(item.quantidade_dias) * Decimal(item.valor_diaria)).quantize(Decimal("0.01"))
        return None

    @safe_route
    def create(self, token_data):
        if not has_permission(token_data, "controle_glosas", "create"):
            return jsonify("Você não possui permissão para criar glosas."), 403
        body = request.get_json(silent=True) or {}
        item = Disallowance(criado_por_usuario_id=token_data.get("id"))
        error = self._apply(item, body, token_data, creating=True)
        if error:
            return jsonify(error), 400
        db.session.add(item)
        db.session.commit()
        socketio.emit("disallowance_update", {"id": item.id, "action": "created"})
        return jsonify({"message": "Glosa registrada.", "id": item.id}), 201

    @safe_route
    def update(self, token_data):
        if not has_permission(token_data, "controle_glosas", "edit"):
            return jsonify("Você não possui permissão para alterar glosas."), 403
        body = request.get_json(silent=True) or {}
        item = db.session.get(Disallowance, body.get("id"))
        if not item:
            return jsonify("Glosa não encontrada."), 404
        if not can_access_cost_center(token_data, item.centro_custo_id):
            return jsonify("Você não possui acesso à filial desta glosa."), 403
        error = self._apply(item, body, token_data)
        if error:
            return jsonify(error), 400
        item.alterado_por_usuario_id = token_data.get("id")
        item.updated_at = dt.now()
        db.session.commit()
        socketio.emit("disallowance_update", {"id": item.id, "action": "updated"})
        return jsonify("Glosa atualizada."), 200

    @safe_route
    def delete(self, token_data):
        if not has_permission(token_data, "controle_glosas", "edit"):
            return jsonify("Você não possui permissão para excluir glosas."), 403
        body = request.get_json(silent=True) or request.args
        item = db.session.get(Disallowance, body.get("id"))
        if not item:
            return jsonify("Glosa não encontrada."), 404
        if not can_access_cost_center(token_data, item.centro_custo_id):
            return jsonify("Você não possui acesso à filial desta glosa."), 403
        item_id = item.id
        db.session.delete(item)
        db.session.commit()
        socketio.emit("disallowance_update", {"id": item_id, "action": "deleted"})
        return jsonify("Glosa excluída."), 200
