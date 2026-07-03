from flask import jsonify, request as rq
from models.movimentos import Movement, db
from models.produtos import Product, db
from utils.safe_route import safe_route
from utils.check_field import check_field

class MovementService:
    def read(self):
        item_id = rq.args.get("item_id")

        query = Movement.query
        if item_id: query = query.filter_by(item_id=item_id)

        movs = query.order_by(Movement.data_hora.desc()).all()
        return jsonify([m.to_dict() for m in movs]), 200

    @safe_route
    def create(self):
        body = rq.get_json()
        item_id = body.get("item_id")
        tipo = body.get("tipo")
        quantidade = body.get("quantidade")
        observacao = body.get("observacao")
        origem = body.get("origem", "desktop")

        ok, error = check_field(item_id=item_id, tipo=tipo, quantidade=quantidade)
        if not ok: return jsonify(error), 400

        if tipo not in ("entrada", "saida"):
            return jsonify("Tipo deve ser 'entrada' ou 'saida'"), 400

        produto = Product.query.filter_by(id=item_id).first()
        if not produto: return jsonify("Produto não encontrado"), 404

        if tipo == "entrada":
            produto.quantidade += quantidade
        else:
            if produto.quantidade < quantidade: return jsonify("Estoque insuficiente para saída"), 400
            produto.quantidade -= quantidade

        new_mov = Movement(
            item_id=item_id, tipo=tipo, quantidade=quantidade,
            observacao=observacao, origem=origem
        )
        db.session.add(new_mov)
        db.session.commit()
        return jsonify("Movimento registrado com sucesso"), 201
