from flask import request as rq, jsonify
from estoque.models.produtos import Products, db
from utils.safe_route import safe_route
from utils.check_field import check_field


class ProductsServices:
    def read(self):
        id = rq.args.get("id")

        if id:
            produto = Products.query.filter_by(id=id).first()
            if not produto: return jsonify("Item não encontrado"), 404
            return jsonify(produto.to_dict()), 200

        produtos = Products.query.all()
        return jsonify([p.to_dict() for p in produtos]), 200
    
    @safe_route
    def create(self):
        body = rq.get_json()
        tipo = body.get("tipo", "GERAL")
        categoria = body.get("categoria")
        unidade = body.get("unidade")
        quantidade = body.get("quantidade", 0)
        quantidade_minima = body.get("quantidade_minima", 0)
        local_estoque = body.get("local_estoque")

        ok, error = check_field(tipo=tipo, categoria=categoria, unidade=unidade, quantidade=quantidade, quantidade_minima=quantidade_minima, local_estoque=local_estoque)
        if not ok: return jsonify(error), 400

        novo_produto = Products(
            tipo=tipo,
            categoria=categoria,
            unidade=unidade,
            quantidade=quantidade,
            quantidade_minima=quantidade_minima,
            local_estoque=local_estoque,
        )

        db.session.add(novo_produto)
        db.session.commit()

        return jsonify("Produto criado com sucesso!"), 201
    
    @safe_route
    def update(self):
        body = rq.get_json()
        id = body.get("id")

        ok, error = check_field(id=id)
        if not ok: return jsonify(error), 400

        produto = Products.query.filter_by(id=id).first()
        if not produto: return jsonify("Item não encontrado"), 404

        campos_editaveis = ["tipo", "categoria", "local_estoque", "unidade"]
        for campo in campos_editaveis:
            if campo in body: setattr(produto, campo, body[campo])

        campos_editaveis_integer = ["quantidade", "quantidade_minima"]
        for campo in campos_editaveis_integer:
            if campo in body: setattr(produto, campo, body[campo])

        db.session.commit()
        return jsonify("Produto atualizado com sucesso!"), 200
    
    @safe_route
    def delete(self):
        id = rq.args.get("id")

        ok, error = check_field(id=id)
        if not ok: return jsonify(error), 400

        produto = Products.query.filter_by(id=id).first()
        if not produto: return jsonify("Item não encontrado"), 404

        db.session.delete(produto)
        db.session.commit()
        return jsonify("Produto removido com sucesso!"), 200
    