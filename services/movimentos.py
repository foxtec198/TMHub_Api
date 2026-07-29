from collections import defaultdict
from datetime import datetime as dt, timedelta

from flask import jsonify, request as rq
from sqlalchemy.orm import selectinload

from models.categorias import Category
from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from models.movimentos import Movement, MovementRecipient
from models.produtos import Product
from models.usuarios import Users
from utils.db import db
from utils.filial_scope import (
    allowed_cost_center_ids,
    apply_cost_center_scope,
    can_access_cost_center,
    is_admin,
)
from utils.safe_route import safe_route


def _positive_int(value, label):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} deve ser um número inteiro.")
    if parsed <= 0:
        raise ValueError(f"{label} deve ser maior que zero.")
    return parsed


def _date(value, end=False):
    if not value:
        return None
    try:
        parsed = dt.strptime(str(value)[:10], "%Y-%m-%d")
    except ValueError as error:
        raise ValueError("Informe o período no formato AAAA-MM-DD.") from error
    return parsed + timedelta(days=1) if end else parsed


class MovementService:
    @staticmethod
    def _is_epi(product):
        category = db.session.get(Category, product.categoria_id) if product else None
        return str(getattr(category, "nome", "") or "").strip().upper() == "EPI"

    @staticmethod
    def _recipient_payload(recipients, token_data):
        if not isinstance(recipients, list):
            raise ValueError("Informe os destinatários em uma lista válida.")
        employee_ids = []
        quantities = {}
        for item in recipients:
            if not isinstance(item, dict):
                raise ValueError("Um ou mais destinatários são inválidos.")
            employee_id = _positive_int(item.get("colaborador_id"), "Colaborador")
            if employee_id in quantities:
                raise ValueError("Não é permitido repetir o mesmo colaborador.")
            quantities[employee_id] = _positive_int(item.get("quantidade"), "Quantidade individual")
            employee_ids.append(employee_id)

        employees = {
            employee.id: employee
            for employee in Employees.query.filter(Employees.id.in_(employee_ids)).all()
        } if employee_ids else {}
        missing = next((employee_id for employee_id in employee_ids if employee_id not in employees), None)
        if missing is not None:
            raise LookupError(f"Colaborador {missing} não encontrado.")

        result = []
        for employee_id in employee_ids:
            employee = employees[employee_id]
            if employee.situacao != 1:
                raise ValueError(f"O colaborador {employee.nome} não está ativo.")
            if not employee.centro_id:
                raise ValueError(f"O colaborador {employee.nome} não possui local ou contrato vinculado.")
            center = db.session.get(CostCenters, employee.centro_id)
            if not center:
                raise ValueError(f"O local do colaborador {employee.nome} não foi encontrado.")
            if not can_access_cost_center(token_data, center.id):
                raise PermissionError(f"Você não possui acesso ao contrato de {employee.nome}.")
            result.append({
                "colaborador_id": employee.id,
                "centro_custo_id": center.id,
                "quantidade": quantities[employee.id],
            })
        return result

    @staticmethod
    def _serialize(movement, employee_map=None, center_map=None, user_map=None, recipients=None):
        recipients = list(movement.destinatarios if recipients is None else recipients)
        employee_map = employee_map or {}
        center_map = center_map or {}
        user_map = user_map or {}
        return {
            **movement.to_dict(),
            "quantidade_total": movement.quantidade,
            "responsavel": user_map.get(movement.usuario_id, "SISTEMA / LEGADO"),
            "destinatarios": [{
                "id": recipient.id,
                "colaborador_id": recipient.colaborador_id,
                "colaborador": employee_map.get(recipient.colaborador_id, f"#{recipient.colaborador_id}"),
                "centro_custo_id": recipient.centro_custo_id,
                "local": center_map.get(recipient.centro_custo_id, f"#{recipient.centro_custo_id}"),
                "quantidade": recipient.quantidade,
            } for recipient in recipients],
        }

    @staticmethod
    def _lookup_maps(movements):
        recipients = [recipient for movement in movements for recipient in movement.destinatarios]
        employee_ids = {recipient.colaborador_id for recipient in recipients}
        center_ids = {recipient.centro_custo_id for recipient in recipients}
        user_ids = {movement.usuario_id for movement in movements if movement.usuario_id}
        employee_map = {
            row.id: f"{row.matricula} - {row.nome}"
            for row in Employees.query.filter(Employees.id.in_(employee_ids)).all()
        } if employee_ids else {}
        center_map = {
            row.id: f"{row.id} - {row.local}"
            for row in CostCenters.query.filter(CostCenters.id.in_(center_ids)).all()
        } if center_ids else {}
        user_map = {
            row.id: row.nome
            for row in Users.query.filter(Users.id.in_(user_ids)).all()
        } if user_ids else {}
        return employee_map, center_map, user_map

    @safe_route
    def read(self, token_data):
        item_id = rq.args.get("item_id", type=int)
        query = Movement.query.options(selectinload(Movement.destinatarios))
        if item_id:
            query = query.filter(Movement.item_id == item_id)
        movements = query.order_by(Movement.data_hora.desc()).all()
        allowed_ids = allowed_cost_center_ids(token_data)
        if allowed_ids is not None:
            movements = [
                movement for movement in movements
                if not movement.destinatarios
                or any(recipient.centro_custo_id in allowed_ids for recipient in movement.destinatarios)
            ]
        employee_map, center_map, user_map = self._lookup_maps(movements)
        return jsonify([
            self._serialize(
                movement,
                employee_map,
                center_map,
                user_map,
                recipients=(
                    movement.destinatarios
                    if allowed_ids is None
                    else [r for r in movement.destinatarios if r.centro_custo_id in allowed_ids]
                ),
            )
            for movement in movements
        ]), 200

    def _validated_data(self, body, token_data):
        try:
            item_id = _positive_int(body.get("item_id", body.get("produto_id")), "Produto")
            quantity = _positive_int(
                body.get("quantidade", body.get("quantidade_total")),
                "Quantidade total",
            )
        except ValueError:
            raise
        movement_type = str(body.get("tipo") or "").strip().lower()
        if movement_type not in {"entrada", "saida"}:
            raise ValueError("Tipo deve ser 'entrada' ou 'saida'.")
        product = Product.query.filter_by(id=item_id).with_for_update().first()
        if not product:
            raise LookupError("Produto não encontrado.")

        raw_recipients = body.get("destinatarios", [])
        recipients = self._recipient_payload(raw_recipients, token_data) if raw_recipients else []
        if movement_type == "entrada" and recipients:
            raise ValueError("Movimentações de entrada não possuem colaboradores destinatários.")
        if movement_type == "saida" and self._is_epi(product) and not recipients:
            raise ValueError("Selecione ao menos um colaborador para a saída de EPI.")
        if recipients and sum(item["quantidade"] for item in recipients) != quantity:
            raise ValueError("A soma das quantidades individuais deve ser igual à quantidade total.")
        return product, movement_type, quantity, recipients

    @staticmethod
    def _apply_stock(product, movement_type, quantity):
        current = int(product.quantidade or 0)
        if movement_type == "entrada":
            product.quantidade = current + quantity
            return
        if current < quantity:
            raise ValueError(
                f"Estoque insuficiente. Disponível: {current}; solicitado: {quantity}."
            )
        product.quantidade = current - quantity

    @staticmethod
    def _reverse_stock(product, movement_type, quantity):
        current = int(product.quantidade or 0)
        if movement_type == "saida":
            product.quantidade = current + quantity
            return
        if current < quantity:
            raise ValueError("Não é possível reverter a entrada porque parte do estoque já foi consumida.")
        product.quantidade = current - quantity

    @safe_route
    def create(self, token_data):
        body = rq.get_json(silent=True) or {}
        try:
            product, movement_type, quantity, recipients = self._validated_data(body, token_data)
            self._apply_stock(product, movement_type, quantity)
        except LookupError as error:
            return jsonify(str(error)), 404
        except PermissionError as error:
            return jsonify(str(error)), 403
        except ValueError as error:
            return jsonify(str(error)), 400

        movement = Movement(
            item_id=product.id,
            produto=product.nome,
            tipo=movement_type,
            quantidade=quantity,
            observacao=body.get("observacao"),
            origem=body.get("origem", "desktop"),
            usuario_id=token_data.get("id"),
        )
        db.session.add(movement)
        db.session.flush()
        for recipient in recipients:
            db.session.add(MovementRecipient(
                movimentacao_id=movement.id,
                **recipient,
            ))
        db.session.commit()
        return jsonify({
            "message": "Movimentação registrada com sucesso.",
            "id": movement.id,
        }), 201

    @safe_route
    def update(self, movement_id, token_data):
        movement = (
            Movement.query
            .options(selectinload(Movement.destinatarios))
            .filter(Movement.id == movement_id)
            .with_for_update()
            .first()
        )
        if not movement:
            return jsonify("Movimentação não encontrada."), 404
        body = rq.get_json(silent=True) or {}
        merged = {
            "item_id": body.get("item_id", movement.item_id),
            "tipo": body.get("tipo", movement.tipo),
            "quantidade": body.get("quantidade", body.get("quantidade_total", movement.quantidade)),
            "destinatarios": body.get("destinatarios", [
                {
                    "colaborador_id": recipient.colaborador_id,
                    "quantidade": recipient.quantidade,
                }
                for recipient in movement.destinatarios
            ]),
        }
        try:
            product, movement_type, quantity, recipients = self._validated_data(merged, token_data)
            old_product = Product.query.filter_by(id=movement.item_id).with_for_update().first()
            if not old_product:
                raise LookupError("Produto original da movimentação não encontrado.")
            self._reverse_stock(old_product, movement.tipo, movement.quantidade)
            self._apply_stock(product, movement_type, quantity)
        except LookupError as error:
            db.session.rollback()
            return jsonify(str(error)), 404
        except PermissionError as error:
            db.session.rollback()
            return jsonify(str(error)), 403
        except ValueError as error:
            db.session.rollback()
            return jsonify(str(error)), 400

        movement.item_id = product.id
        movement.produto = product.nome
        movement.tipo = movement_type
        movement.quantidade = quantity
        if "observacao" in body:
            movement.observacao = body.get("observacao")
        MovementRecipient.query.filter_by(movimentacao_id=movement.id).delete()
        for recipient in recipients:
            db.session.add(MovementRecipient(movimentacao_id=movement.id, **recipient))
        db.session.commit()
        return jsonify("Movimentação atualizada com sucesso."), 200

    @safe_route
    def delete(self, movement_id, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem excluir movimentações."), 403
        movement = Movement.query.filter_by(id=movement_id).with_for_update().first()
        if not movement:
            return jsonify("Movimentação não encontrada."), 404
        product = Product.query.filter_by(id=movement.item_id).with_for_update().first()
        if not product:
            return jsonify("Produto da movimentação não encontrado."), 404
        try:
            self._reverse_stock(product, movement.tipo, movement.quantidade)
        except ValueError as error:
            return jsonify(str(error)), 409
        db.session.delete(movement)
        db.session.commit()
        return jsonify("Movimentação removida e estoque revertido com sucesso."), 200

    @safe_route
    def dashboard(self, token_data):
        try:
            start = _date(rq.args.get("inicio"))
            end = _date(rq.args.get("fim"), end=True)
        except ValueError as error:
            return jsonify(str(error)), 400
        product_id = rq.args.get("produto_id", type=int)
        movement_type = str(rq.args.get("tipo") or "").strip().lower() or None
        employee_id = rq.args.get("colaborador_id", type=int)
        center_id = rq.args.get("centro_custo_id", type=int)
        if movement_type and movement_type not in {"entrada", "saida"}:
            return jsonify("Tipo de movimentação inválido."), 400
        if center_id and not can_access_cost_center(token_data, center_id):
            return jsonify("Você não possui acesso a este contrato."), 403

        query = Movement.query.options(selectinload(Movement.destinatarios))
        if start:
            query = query.filter(Movement.data_hora >= start)
        if end:
            query = query.filter(Movement.data_hora < end)
        if product_id:
            query = query.filter(Movement.item_id == product_id)
        if movement_type:
            query = query.filter(Movement.tipo == movement_type)
        movements = query.order_by(Movement.data_hora.desc()).all()

        allowed_ids = allowed_cost_center_ids(token_data)
        filtered = []
        for movement in movements:
            recipients = list(movement.destinatarios)
            if allowed_ids is not None and recipients:
                recipients = [r for r in recipients if r.centro_custo_id in allowed_ids]
                if not recipients:
                    continue
            if employee_id:
                recipients = [r for r in recipients if r.colaborador_id == employee_id]
                if not recipients:
                    continue
            if center_id:
                recipients = [r for r in recipients if r.centro_custo_id == center_id]
                if not recipients:
                    continue
            visible_quantity = (
                sum(recipient.quantidade for recipient in recipients)
                if movement.destinatarios and (
                    employee_id or center_id or allowed_ids is not None
                )
                else movement.quantidade
            )
            filtered.append((movement, recipients, visible_quantity))

        products_query = Product.query
        if product_id:
            products_query = products_query.filter(Product.id == product_id)
        products = products_query.order_by(Product.nome).all()
        category_map = {
            category.id: str(category.nome or "").strip().upper()
            for category in Category.query.all()
        }
        product_map = {product.id: product for product in Product.query.all()}
        employee_map, center_map, user_map = self._lookup_maps([item[0] for item in filtered])

        entries = sum(quantity for movement, _, quantity in filtered if movement.tipo == "entrada")
        outputs = sum(quantity for movement, _, quantity in filtered if movement.tipo == "saida")
        moved_by_product = defaultdict(int)
        daily = defaultdict(lambda: {"entrada": 0, "saida": 0})
        delivered_by_employee = defaultdict(int)
        delivered_by_center = defaultdict(int)
        epi_delivered = 0
        for movement, recipients, quantity in filtered:
            moved_by_product[movement.item_id] += quantity
            key = movement.data_hora.date().isoformat()
            daily[key][movement.tipo] += quantity
            product = product_map.get(movement.item_id)
            is_epi = category_map.get(getattr(product, "categoria_id", None)) == "EPI"
            if movement.tipo == "saida" and is_epi:
                for recipient in recipients:
                    epi_delivered += recipient.quantidade
                    delivered_by_employee[recipient.colaborador_id] += recipient.quantidade
                    delivered_by_center[recipient.centro_custo_id] += recipient.quantidade

        scoped_centers = (
            apply_cost_center_scope(CostCenters.query, CostCenters.id, token_data)
            .order_by(CostCenters.local)
            .all()
        )
        return jsonify({
            "indicadores": {
                "produtos": len(products),
                "itens_estoque": sum(int(product.quantidade or 0) for product in products),
                "entradas": entries,
                "saidas": outputs,
                "estoque_baixo": sum(
                    1 for product in products
                    if int(product.quantidade or 0) > 0
                    and int(product.quantidade or 0) <= int(product.quantidade_minima or 0)
                ),
                "sem_estoque": sum(1 for product in products if int(product.quantidade or 0) <= 0),
                "epis_entregues": epi_delivered,
            },
            "estoque_baixo": [{
                "id": product.id,
                "produto": product.nome,
                "quantidade": product.quantidade,
                "minimo": product.quantidade_minima,
                "unidade": product.unidade,
            } for product in products if int(product.quantidade or 0) <= int(product.quantidade_minima or 0)],
            "mais_movimentados": [{
                "produto_id": item_id,
                "produto": getattr(product_map.get(item_id), "nome", f"#{item_id}"),
                "quantidade": quantity,
            } for item_id, quantity in sorted(
                moved_by_product.items(), key=lambda item: item[1], reverse=True
            )[:10]],
            "serie": [
                {"data": day, **values}
                for day, values in sorted(daily.items())
            ],
            "epis_por_colaborador": [{
                "colaborador_id": item_id,
                "colaborador": employee_map.get(item_id, f"#{item_id}"),
                "quantidade": quantity,
            } for item_id, quantity in sorted(
                delivered_by_employee.items(), key=lambda item: item[1], reverse=True
            )[:10]],
            "epis_por_local": [{
                "centro_custo_id": item_id,
                "local": center_map.get(item_id, f"#{item_id}"),
                "quantidade": quantity,
            } for item_id, quantity in sorted(
                delivered_by_center.items(), key=lambda item: item[1], reverse=True
            )[:10]],
            "recentes": [
                self._serialize(movement, employee_map, center_map, user_map, recipients)
                for movement, recipients, _ in filtered[:15]
            ],
            "filtros": {
                "produtos": [{"label": product.nome, "value": product.id} for product in Product.query.order_by(Product.nome).all()],
                "colaboradores": [{
                    "label": label,
                    "value": employee_id,
                } for employee_id, label in sorted(
                    employee_map.items(), key=lambda item: item[1]
                )],
                "centros_custo": [{
                    "label": f"{center.id} - {center.local}",
                    "value": center.id,
                } for center in scoped_centers],
            },
        }), 200
