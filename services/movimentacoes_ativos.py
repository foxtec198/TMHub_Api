# Regras de negócio de movimentações de ativos.
# Dependências externas.
from flask import jsonify, request
from sqlalchemy import or_

# Módulos internos da aplicação.
from models.centros_de_custo import CostCenters
from models.estrutura import StructureAsset, StructureLocation
from models.movimentacoes_ativos import StructureAssetMovement
from models.usuarios import Users
from utils.db import db
from utils.filial_scope import (
    allowed_cost_center_ids,
    apply_cost_center_scope,
    can_access_cost_center,
)
from utils.safe_route import safe_route


def _integer(value, label):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} inválido.")
    if parsed <= 0:
        raise ValueError(f"{label} inválido.")
    return parsed


def _text(value):
    return str(value or "").strip()


class StructureAssetMovementService:
    @staticmethod
    def _center_label(center):
        if not center:
            return None
        return f"{center.id} - {center.local}"

    @staticmethod
    def _serialize(movement, assets, centers, locations, users):
        asset = assets.get(movement.ativo_id)
        return {
            "id": movement.id,
            "tipo": movement.tipo,
            "data_hora": movement.data_hora.isoformat() if movement.data_hora else None,
            "ativo_id": movement.ativo_id,
            "ativo": asset.nome if asset else f"Ativo #{movement.ativo_id}",
            "patrimonio": asset.patrimonio if asset else None,
            "categoria": asset.categoria if asset else None,
            "centro_custo_origem_id": movement.centro_custo_origem_id,
            "origem": StructureAssetMovementService._center_label(
                centers.get(movement.centro_custo_origem_id)
            ) or "Carga inicial",
            "local_origem": getattr(locations.get(movement.local_origem_id), "nome", None),
            "centro_custo_destino_id": movement.centro_custo_destino_id,
            "destino": StructureAssetMovementService._center_label(
                centers.get(movement.centro_custo_destino_id)
            ),
            "local_destino": getattr(locations.get(movement.local_destino_id), "nome", None),
            "observacao": movement.observacao,
            "usuario_id": movement.usuario_id,
            "responsavel": users.get(movement.usuario_id, "SISTEMA / CARGA INICIAL"),
        }

    @safe_route
    def read(self, token_data):
        scoped_center_ids = allowed_cost_center_ids(token_data)

        movement_query = StructureAssetMovement.query
        if scoped_center_ids is not None:
            movement_query = movement_query.filter(or_(
                StructureAssetMovement.centro_custo_origem_id.in_(scoped_center_ids),
                StructureAssetMovement.centro_custo_destino_id.in_(scoped_center_ids),
            ))
        movements = movement_query.order_by(
            StructureAssetMovement.data_hora.desc(),
            StructureAssetMovement.id.desc(),
        ).all()

        assets = (
            apply_cost_center_scope(
                StructureAsset.query,
                StructureAsset.centro_custo_id,
                token_data,
            )
            .order_by(StructureAsset.nome, StructureAsset.patrimonio)
            .all()
        )
        centers = (
            apply_cost_center_scope(
                CostCenters.query,
                CostCenters.id,
                token_data,
            )
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

        movement_asset_ids = {item.ativo_id for item in movements}
        movement_center_ids = {
            center_id
            for item in movements
            for center_id in (
                item.centro_custo_origem_id,
                item.centro_custo_destino_id,
            )
            if center_id
        }
        movement_location_ids = {
            location_id
            for item in movements
            for location_id in (item.local_origem_id, item.local_destino_id)
            if location_id
        }
        user_ids = {item.usuario_id for item in movements if item.usuario_id}

        asset_map = {item.id: item for item in assets}
        missing_asset_ids = movement_asset_ids.difference(asset_map)
        if missing_asset_ids:
            asset_map.update({
                item.id: item
                for item in StructureAsset.query.filter(
                    StructureAsset.id.in_(missing_asset_ids)
                ).all()
            })

        center_map = {item.id: item for item in centers}
        missing_center_ids = movement_center_ids.difference(center_map)
        if missing_center_ids:
            center_map.update({
                item.id: item
                for item in CostCenters.query.filter(
                    CostCenters.id.in_(missing_center_ids)
                ).all()
            })

        location_map = {item.id: item for item in locations}
        missing_location_ids = movement_location_ids.difference(location_map)
        if missing_location_ids:
            location_map.update({
                item.id: item
                for item in StructureLocation.query.filter(
                    StructureLocation.id.in_(missing_location_ids)
                ).all()
            })

        user_map = {
            item.id: item.nome
            for item in Users.query.filter(Users.id.in_(user_ids)).all()
        } if user_ids else {}

        return jsonify({
            "movimentacoes": [
                self._serialize(item, asset_map, center_map, location_map, user_map)
                for item in movements
            ],
            "ativos": [{
                "id": item.id,
                "nome": item.nome,
                "categoria": item.categoria,
                "patrimonio": item.patrimonio,
                "centro_custo_id": item.centro_custo_id,
                "local_id": item.local_id,
                "label": f"{item.patrimonio} - {item.nome}",
                "origem": self._center_label(center_map.get(item.centro_custo_id)),
                "local": getattr(location_map.get(item.local_id), "nome", None),
            } for item in assets],
            "centros_custo": [{
                "id": item.id,
                "departamento": item.departamento,
                "local": item.local,
                "label": f"{item.id} - {item.local}",
            } for item in centers],
            "locais": [{
                "id": item.id,
                "centro_custo_id": item.centro_custo_id,
                "nome": item.nome,
            } for item in locations],
        }), 200

    @safe_route
    def create(self, token_data):
        body = request.get_json(silent=True) or {}
        try:
            asset_id = _integer(body.get("ativo_id"), "Ativo")
            destination_center_id = _integer(
                body.get("centro_custo_destino_id"),
                "Contrato de destino",
            )
        except ValueError as error:
            return jsonify(str(error)), 400

        asset = (
            StructureAsset.query
            .filter(StructureAsset.id == asset_id)
            .with_for_update()
            .first()
        )
        if not asset:
            return jsonify("Ativo não encontrado."), 404
        if not can_access_cost_center(token_data, asset.centro_custo_id):
            return jsonify("Você não possui acesso ao contrato de origem deste ativo."), 403
        if not can_access_cost_center(token_data, destination_center_id):
            return jsonify("Você não possui acesso ao contrato de destino."), 403

        destination_center = db.session.get(CostCenters, destination_center_id)
        if not destination_center:
            return jsonify("Contrato de destino não encontrado."), 404

        destination_location_id = body.get("local_destino_id") or None
        destination_location = None
        if destination_location_id:
            try:
                destination_location_id = _integer(
                    destination_location_id,
                    "Local de destino",
                )
            except ValueError as error:
                return jsonify(str(error)), 400
            destination_location = db.session.get(
                StructureLocation,
                destination_location_id,
            )
            if (
                not destination_location
                or destination_location.centro_custo_id != destination_center_id
            ):
                return jsonify("O local informado não pertence ao contrato de destino."), 400

        if (
            asset.centro_custo_id == destination_center_id
            and asset.local_id == destination_location_id
        ):
            return jsonify("O ativo já está alocado neste contrato e local."), 409

        movement = StructureAssetMovement(
            ativo_id=asset.id,
            tipo="transferencia",
            centro_custo_origem_id=asset.centro_custo_id,
            centro_custo_destino_id=destination_center_id,
            local_origem_id=asset.local_id,
            local_destino_id=destination_location_id,
            usuario_id=token_data.get("id"),
            observacao=_text(body.get("observacao")) or None,
        )
        asset.centro_custo_id = destination_center_id
        asset.local_id = destination_location_id

        db.session.add(movement)
        db.session.commit()

        return jsonify({
            "message": "Ativo movimentado com sucesso.",
            "movimentacao_id": movement.id,
            "ativo_id": asset.id,
        }), 201

