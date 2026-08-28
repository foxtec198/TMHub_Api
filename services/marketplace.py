from flask import jsonify, request

from models.marketplace import MarketplaceProduct, MarketplacePurchase
from models.uso_tmhub import TMHubEdinhoLedger
from utils.db import db
from utils.filial_scope import is_admin
from utils.safe_route import safe_route


class MarketplaceService:
    DEFAULT_PRODUCTS = (
        ("Tema Aurora", "Tema visual claro para o TMHub.", "tema", 100),
        ("Tema Eclipse", "Tema visual escuro para o TMHub.", "tema", 150),
        ("Skin Timo Neon", "Personalização experimental do Timo.", "skin", 250),
    )

    @staticmethod
    def _ensure_catalog():
        if MarketplaceProduct.query.count():
            return
        for nome, descricao, categoria, preco in MarketplaceService.DEFAULT_PRODUCTS:
            db.session.add(MarketplaceProduct(nome=nome, descricao=descricao, categoria=categoria, preco_edinhos=preco))
        db.session.commit()

    @staticmethod
    def _balance(user_id):
        return int(db.session.query(db.func.coalesce(db.func.sum(TMHubEdinhoLedger.quantidade), 0)).filter(TMHubEdinhoLedger.usuario_id == user_id).scalar() or 0)

    @staticmethod
    def _product(product):
        return {"id": product.id, "nome": product.nome, "descricao": product.descricao, "categoria": product.categoria, "preco_edinhos": product.preco_edinhos, "ativo": product.ativo}

    @safe_route
    def catalog(self, token_data):
        if not is_admin(token_data):
            return jsonify("O marketplace está disponível somente para administradores durante os testes."), 403
        self._ensure_catalog()
        return jsonify({"saldo_edinhos": self._balance(token_data["id"]), "produtos": [self._product(item) for item in MarketplaceProduct.query.filter_by(ativo=True).order_by(MarketplaceProduct.categoria, MarketplaceProduct.nome).all()]}), 200

    @safe_route
    def purchases(self, token_data):
        if not is_admin(token_data):
            return jsonify("O marketplace está disponível somente para administradores durante os testes."), 403
        rows = MarketplacePurchase.query.filter_by(usuario_id=token_data["id"]).order_by(MarketplacePurchase.created_at.desc()).all()
        return jsonify({"saldo_edinhos": self._balance(token_data["id"]), "compras": [{"id": item.id, "produto": self._product(item.produto), "preco_edinhos": item.preco_edinhos, "status": item.status, "created_at": item.created_at.isoformat()} for item in rows]}), 200

    @safe_route
    def buy(self, token_data):
        if not is_admin(token_data):
            return jsonify("O marketplace está disponível somente para administradores durante os testes."), 403
        body = request.get_json(silent=True) or {}
        try:
            product_id = int(body.get("produto_id"))
        except (TypeError, ValueError):
            return jsonify("Selecione um produto válido."), 400
        product = MarketplaceProduct.query.filter_by(id=product_id, ativo=True).with_for_update().first()
        if not product:
            return jsonify("Produto não encontrado ou indisponível."), 404
        balance = self._balance(token_data["id"])
        if balance < product.preco_edinhos:
            return jsonify({"message": "Saldo insuficiente.", "saldo_edinhos": balance, "necessario": product.preco_edinhos}), 409
        purchase = MarketplacePurchase(usuario_id=token_data["id"], produto_id=product.id, preco_edinhos=product.preco_edinhos)
        db.session.add(purchase)
        db.session.add(TMHubEdinhoLedger(usuario_id=token_data["id"], tipo="marketplace_compra", quantidade=-product.preco_edinhos, descricao=f"Compra: {product.nome}"))
        db.session.commit()
        return jsonify({"compra": {"id": purchase.id, "produto": self._product(product), "preco_edinhos": purchase.preco_edinhos, "status": purchase.status, "created_at": purchase.created_at.isoformat()}, "saldo_edinhos": self._balance(token_data["id"])}), 201
