from flask import request as rq, jsonify
from estoque.models.movimentacoes import Movements, db
from estoque.models.produtos import Products, db
from utils.safe_route import safe_route
from utils.check_field import check_field

class MovementsServices:
    @safe_route
    def read(self):
        id = rq.args.get("id")

        if id:
            mov = Movements.query.filter_by(id=id).first()
            if not mov: return jsonify("Movimento não encontrado"), 404
            return jsonify(mov.to_dict()), 200

        movs = Movements.query.all()
        return jsonify([m.to_dict() for m in movs]), 200
    
    @safe_route
    def create(self):
        body = rq.get_json()
        produto_id = body.get("produto_id")
        tipo = body.get("tipo")
        quantidade = body.get("quantidade")
        local_destino = body.get("local_destino")
        sup = body.get("sup")

        ok, error = check_field(produto_id=produto_id, tipo=tipo, quantidade=quantidade)
        if not ok: return jsonify(error), 400

        produto = Products.query.filter_by(produto_id=produto_id).first()
        if not produto: return jsonify("Produto não encontrado"), 404

        tipo = str(tipo).upper()
        if tipo not in ("ENTRADA", "SAIDA"):
            return jsonify("Tipo inválido, use ENTRADA ou SAIDA"), 400

        if tipo == "SAIDA" and produto.quantidade < quantidade:
            return jsonify("Estoque insuficiente para essa saída"), 400
        
        produto.quantidade += quantidade if tipo == "ENTRADA" else -quantidade

        nova_mov = Movements(
            produto_id=produto_id,
            tipo=tipo,
            quantidade=quantidade,
            sup=sup,
            local_destino=local_destino,
        )

        db.session.add(nova_mov)
        db.session.commit()

        return jsonify("Movimentação registrada com sucesso!"), 201

    @safe_route
    def update(self):
        ...

    @safe_route
    def delete(self):
        ...