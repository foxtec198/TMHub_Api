from flask import jsonify, request

from models.centros_de_custo import CostCenters
from models.estrutura import StructureAsset, StructureLocation
from models.supervisores import Supervisors
from utils.db import db
from utils.filial_scope import apply_cost_center_scope, can_access_cost_center
from utils.safe_route import safe_route


def _text(value):
    return str(value or "").strip()


class StructureService:
    @safe_route
    def read(self, token_data):
        centers = (
            apply_cost_center_scope(CostCenters.query, CostCenters.id, token_data)
            .order_by(CostCenters.departamento, CostCenters.local)
            .all()
        )
        center_ids = [center.id for center in centers]
        locations = (
            StructureLocation.query
            .filter(StructureLocation.centro_custo_id.in_(center_ids))
            .order_by(StructureLocation.nome)
            .all()
            if center_ids else []
        )
        assets = (
            StructureAsset.query
            .filter(StructureAsset.centro_custo_id.in_(center_ids))
            .order_by(StructureAsset.nome)
            .all()
            if center_ids else []
        )
        supervisor_ids = {center.supervisor_id for center in centers if center.supervisor_id}
        supervisors = {
            row.id: row.nome
            for row in Supervisors.query.filter(Supervisors.id.in_(supervisor_ids)).all()
        } if supervisor_ids else {}
        locations_by_center = {}
        assets_by_center = {}
        for item in locations:
            locations_by_center.setdefault(item.centro_custo_id, []).append(item.to_dict())
        for item in assets:
            assets_by_center.setdefault(item.centro_custo_id, []).append(item.to_dict())

        departments = {}
        for center in centers:
            department = str(center.departamento or "SEM DEPARTAMENTO")
            departments.setdefault(department, []).append({
                "id": center.id,
                "contrato": center.local,
                "supervisor": supervisors.get(center.supervisor_id) or "SEM SUPERVISOR",
                "locais": locations_by_center.get(center.id, []),
                "ativos": assets_by_center.get(center.id, []),
            })
        return jsonify([
            {"departamento": department, "contratos": contracts}
            for department, contracts in departments.items()
        ])

    @safe_route
    def create(self, token_data):
        body = request.get_json(silent=True) or {}
        kind = _text(body.get("tipo")).lower()
        try:
            center_id = int(body.get("centro_custo_id"))
        except (TypeError, ValueError):
            return jsonify("Selecione um contrato válido."), 400
        if not can_access_cost_center(token_data, center_id):
            return jsonify("Você não possui acesso à filial deste contrato."), 403
        if not db.session.get(CostCenters, center_id):
            return jsonify("Contrato não encontrado."), 404

        name = _text(body.get("nome"))
        if not name:
            return jsonify("Informe o nome."), 400
        description = _text(body.get("descricao")) or None

        if kind == "local":
            duplicate = StructureLocation.query.filter(
                StructureLocation.centro_custo_id == center_id,
                db.func.lower(StructureLocation.nome) == name.lower(),
            ).first()
            if duplicate:
                return jsonify("Este local já está cadastrado no contrato."), 409
            item = StructureLocation(
                centro_custo_id=center_id,
                nome=name.upper(),
                descricao=description,
            )
        elif kind == "ativo":
            category = _text(body.get("categoria"))
            if not category:
                return jsonify("Informe o tipo/categoria do ativo."), 400
            local_id = body.get("local_id") or None
            if local_id:
                try:
                    local_id = int(local_id)
                except (TypeError, ValueError):
                    return jsonify("Local inválido."), 400
                local = db.session.get(StructureLocation, local_id)
                if not local or local.centro_custo_id != center_id:
                    return jsonify("O local selecionado não pertence a este contrato."), 400
            patrimonio = _text(body.get("patrimonio")).upper()
            if patrimonio and StructureAsset.query.filter_by(patrimonio=patrimonio).first():
                return jsonify("Este patrimônio já está cadastrado."), 409
            item = StructureAsset(
                centro_custo_id=center_id,
                local_id=local_id,
                nome=name.upper(),
                categoria=category.upper(),
                patrimonio=patrimonio or "PENDENTE",
                descricao=description,
            )
            db.session.add(item)
            db.session.flush()
            if not patrimonio:
                item.patrimonio = f"TMH-{center_id}-{item.id:06d}"
        else:
            return jsonify("Escolha entre local ou ativo."), 400

        db.session.add(item)
        db.session.commit()
        return jsonify({"message": "Cadastro realizado com sucesso.", "item": item.to_dict()}), 201

    @safe_route
    def delete(self, token_data):
        body = request.get_json(silent=True) or {}
        kind = _text(body.get("tipo")).lower()
        try:
            item_id = int(body.get("id"))
        except (TypeError, ValueError):
            return jsonify("Registro inválido."), 400

        model = {"local": StructureLocation, "ativo": StructureAsset}.get(kind)
        if not model:
            return jsonify("Escolha entre local ou ativo."), 400
        item = db.session.get(model, item_id)
        if not item:
            return jsonify("Registro não encontrado."), 404
        if not can_access_cost_center(token_data, item.centro_custo_id):
            return jsonify("Você não possui acesso à filial deste contrato."), 403

        db.session.delete(item)
        db.session.commit()
        return jsonify("Registro excluído com sucesso."), 200
