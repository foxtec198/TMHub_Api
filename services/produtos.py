from flask import jsonify, request as rq
from models.produtos import Product, db
from utils.safe_route import safe_route
from utils.check_field import check_field

class ProductService:
    def read(self):
        id = rq.args.get("id")

        if id:
            prod = Product.query.filter_by(id=id).first()
            if not prod: return jsonify("Produto não encontrado"), 404
            return jsonify(prod.to_dict()), 200

        prods = Product.query.all()
        return jsonify([p.to_dict() for p in prods]), 200

    @safe_route
    def create(self):
        body = rq.get_json()
        nome = body.get("nome")
        categoria_id = body.get("categoria_id")
        unidade = body.get("unidade")
        quantidade = body.get("quantidade", 0)
        quantidade_minima = body.get("quantidade_minima", 0)
        local_estoque = body.get("local_estoque")

        ok, error = check_field(nome=nome, categoria_id=categoria_id, unidade=unidade)
        if not ok: return jsonify(error), 400

        new_prod = Product(
            nome=nome.upper(), categoria_id=categoria_id, unidade=unidade,
            quantidade=quantidade, quantidade_minima=quantidade_minima,
            local_estoque=local_estoque
        )
        db.session.add(new_prod)
        db.session.commit()
        return jsonify("Produto criado com sucesso"), 201

    @safe_route
    def update(self):
        body = rq.get_json()
        id = body.get("id")

        ok, error = check_field(id=id)
        if not ok: return jsonify(error), 400

        prod = Product.query.filter_by(id=id).first()
        if not prod: return jsonify("Produto não encontrado"), 404

        campos = ("nome", "categoria_id", "unidade", "quantidade", "quantidade_minima", "local_estoque")
        for campo in campos:
            if campo in body: setattr(prod, campo, body[campo])

        db.session.commit()
        return jsonify("Produto atualizado com sucesso"), 200

    @safe_route
    def delete(self):
        id = rq.args.get("id")

        ok, error = check_field(id=id)
        if not ok: return jsonify(error), 400

        prod = Product.query.filter_by(id=id).first()
        if not prod: return jsonify("Produto não encontrado"), 404

        db.session.delete(prod)
        db.session.commit()
        return jsonify("Produto removido com sucesso"), 200
