# Regras de negócio de categorias.
# Dependências externas.
from flask import jsonify, request as rq
# Módulos internos da aplicação.
from models.categorias import Category, db
from utils.safe_route import safe_route
from utils.check_field import check_field

class CategoryService:
    def read(self):
        id = rq.args.get("id")

        if id:
            cat = Category.query.filter_by(id=id).first()
            if not cat: return jsonify("Categoria não encontrada"), 404
            return jsonify(cat.to_dict()), 200

        cats = Category.query.all()
        return jsonify([c.to_dict() for c in cats]), 200

    @safe_route
    def create(self):
        body = rq.get_json()
        nome = body.get("nome")
        descricao = body.get("descricao")

        ok, error = check_field(nome=nome)
        if not ok: return jsonify(error), 400

        new_cat = Category(nome=nome.upper(), descricao=descricao)
        db.session.add(new_cat)
        db.session.commit()
        return jsonify("Categoria criada com sucesso"), 201

    @safe_route
    def update(self):
        body = rq.get_json()
        id = body.get("id")

        ok, error = check_field(id=id)
        if not ok: return jsonify(error), 400

        cat = Category.query.filter_by(id=id).first()
        if not cat: return jsonify("Categoria não encontrada"), 404

        if "nome" in body: cat.nome = body["nome"].upper()
        if "descricao" in body: cat.descricao = body["descricao"]

        db.session.commit()
        return jsonify("Categoria atualizada com sucesso"), 200

    @safe_route
    def delete(self):
        id = rq.args.get("id")

        ok, error = check_field(id=id)
        if not ok: return jsonify(error), 400

        cat = Category.query.filter_by(id=id).first()
        if not cat: return jsonify("Categoria não encontrada"), 404

        db.session.delete(cat)
        db.session.commit()
        return jsonify("Categoria removida com sucesso"), 200
