"""Marketplace de personalizações comprado com o livro-caixa de Edinhos."""
from datetime import datetime
import re
import unicodedata

from flask import jsonify, request

from models.marketplace import MarketplaceProduct, MarketplacePurchase
from models.uso_tmhub import TMHubEdinhoLedger
from models.usuarios import Users
from utils.db import db
from utils.safe_route import safe_route
from utils.theme_access import DEFAULT_THEME


class MarketplaceService:
    # Código é contrato: o frontend usa o sufixo dos temas e o código completo
    # dos adornos para aplicar a personalização comprada.
    DEFAULT_PRODUCTS = (
        {"codigo": "tema_tmhub", "nome": "TMHub Original", "descricao": "A identidade institucional clássica do TMHub.", "categoria": "tema", "preco": 0, "destaque": False, "reembolsavel": False},
        {"codigo": "tema_aurora", "nome": "Aurora", "descricao": "Índigo, violeta e verde-luz em uma atmosfera elegante.", "categoria": "tema", "preco": 120, "destaque": True},
        {"codigo": "tema_cyberpunk", "nome": "Cyberpunk", "descricao": "Cyan, vermelho neon e alto contraste futurista.", "categoria": "tema", "preco": 140},
        {"codigo": "tema_pride", "nome": "Orgulho", "descricao": "Uma identidade vibrante inspirada nas cores do orgulho.", "categoria": "tema", "preco": 100},
        {"codigo": "tema_christmas", "nome": "Natal", "descricao": "Pinheiro, vinho e dourado para o fim de ano.", "categoria": "tema", "preco": 100},
        {"codigo": "tema_ocean", "nome": "Ocean", "descricao": "Azul oceano e ciano para uma navegação serena.", "categoria": "tema", "preco": 120},
        {"codigo": "tema_sunset", "nome": "Sunset", "descricao": "Âmbar, coral e tons noturnos de pôr do sol.", "categoria": "tema", "preco": 120},
        {"codigo": "tema_forest", "nome": "Forest", "descricao": "Verde profundo, natureza e detalhes dourados.", "categoria": "tema", "preco": 120},
        {"codigo": "tema_terminal", "nome": "Terminal", "descricao": "Grafite com verde fósforo para quem vive no código.", "categoria": "tema", "preco": 140},
        {"codigo": "tema_paper", "nome": "Paper", "descricao": "Papel claro, tinta e uma leitura mais editorial.", "categoria": "tema", "preco": 100},
        {"codigo": "tema_muertos", "nome": "Día de los Muertos", "descricao": "Vinho, violeta e cempasúchil em uma edição especial.", "categoria": "tema", "preco": 120},
        {"codigo": "adorno_halloween", "nome": "Halloween", "descricao": "Moldura roxa e laranja com detalhes assustadoramente divertidos.", "categoria": "adorno", "preco": 90, "destaque": True},
        {"codigo": "adorno_natal", "nome": "Natal", "descricao": "Neve, vermelho e verde ao redor da sua foto.", "categoria": "adorno", "preco": 90},
        {"codigo": "adorno_gptw", "nome": "Great Place to Work", "descricao": "Adorno comemorativo azul e dourado para celebrar a conquista.", "categoria": "adorno", "preco": 110, "destaque": True},
        {"codigo": "adorno_aniversario", "nome": "Aniversário", "descricao": "Confetes e cores para deixar o seu dia em evidência.", "categoria": "adorno", "preco": 75},
        {"codigo": "adorno_orgulho", "nome": "Orgulho", "descricao": "Um aro multicolorido para personalizar a foto de perfil.", "categoria": "adorno", "preco": 80},
        {"codigo": "adorno_conquista", "nome": "Conquista", "descricao": "Estrelas douradas para celebrar metas e reconhecimentos.", "categoria": "adorno", "preco": 100},
        {"codigo": "timo_gold", "nome": "Timo Gold Premium", "descricao": "Metal escovado, brilho champanhe e acabamento premium para o Timo.", "categoria": "timo_skin", "preco": 20000, "destaque": True},
        {"codigo": "timo_cyber", "nome": "Timo Cyber Premium", "descricao": "Acabamento neon cyan com detalhes em vermelho para o Timo.", "categoria": "timo_skin", "preco": 2000, "destaque": True},
        {"codigo": "timo_cenario_christmas", "nome": "Oficina de Natal", "descricao": "Uma oficina iluminada, cercada por neve, presentes e o aconchego do Natal.", "categoria": "timo_cenario", "preco": 500, "destaque": True},
        {"codigo": "timo_cenario_halloween", "nome": "Noite de Halloween", "descricao": "Laboratório noturno com abóboras, névoa e luzes misteriosamente divertidas.", "categoria": "timo_cenario", "preco": 500, "destaque": True},
        {"codigo": "timo_cenario_muertos", "nome": "Jardim de Cempasúchil", "descricao": "Uma celebração luminosa de memórias entre flores, velas e cores vibrantes.", "categoria": "timo_cenario", "preco": 500, "destaque": True},
        {"codigo": "timo_cenario_cyber", "nome": "Escritório Cyberpunk", "descricao": "Escritório holográfico premium, com partículas digitais, glitches sutis e uma plataforma exclusiva para o Timo.", "categoria": "timo_cenario", "preco": 1200, "destaque": True},
    )

    @staticmethod
    def _normalize(value):
        text = unicodedata.normalize("NFD", str(value or "").lower())
        return re.sub(r"[^a-z0-9]+", " ", "".join(char for char in text if not unicodedata.combining(char))).strip()

    @classmethod
    def _ensure_catalog(cls):
        definitions = {item["codigo"]: item for item in cls.DEFAULT_PRODUCTS}
        by_name = {cls._normalize(item["nome"]): item for item in cls.DEFAULT_PRODUCTS}
        rows = MarketplaceProduct.query.order_by(MarketplaceProduct.id).all()

        for row in rows:
            if not row.codigo:
                definition = by_name.get(cls._normalize(row.nome))
                code_in_use = definition and MarketplaceProduct.query.filter_by(codigo=definition["codigo"]).first()
                row.codigo = definition["codigo"] if definition and not code_in_use else f"legado_{row.id}"
                if not definition or code_in_use:
                    row.ativo = False

        current = {row.codigo: row for row in rows}
        for code, definition in definitions.items():
            row = current.get(code)
            if not row:
                row = MarketplaceProduct(codigo=code)
                db.session.add(row)
            row.nome = definition["nome"]
            row.descricao = definition["descricao"]
            row.categoria = definition["categoria"]
            row.preco_edinhos = definition["preco"]
            row.destaque = bool(definition.get("destaque"))
            row.reembolsavel = bool(definition.get("reembolsavel", True))
            row.ativo = True
        db.session.commit()

    @staticmethod
    def _balance(user_id):
        return int(db.session.query(db.func.coalesce(db.func.sum(TMHubEdinhoLedger.quantidade), 0)).filter(TMHubEdinhoLedger.usuario_id == user_id).scalar() or 0)

    @staticmethod
    def _is_equipped(product, user):
        if product.categoria == "tema":
            return product.codigo == f"tema_{user.tema or DEFAULT_THEME}"
        if product.categoria == "adorno":
            return product.codigo == user.adorno_foto
        if product.categoria == "timo_skin":
            return product.codigo == (user.timo_skin or "default")
        if product.categoria == "timo_cenario":
            return product.codigo == f"timo_cenario_{user.timo_cenario or 'workshop'}"
        return False

    @classmethod
    def _product(cls, product, user=None, owned_ids=None):
        owned = product.codigo == "tema_tmhub" or bool(owned_ids and product.id in owned_ids)
        return {
            "id": product.id, "codigo": product.codigo, "nome": product.nome,
            "descricao": product.descricao, "categoria": product.categoria,
            "preco_edinhos": product.preco_edinhos, "destaque": bool(product.destaque),
            "reembolsavel": bool(product.reembolsavel), "ativo": bool(product.ativo),
            "adquirido": owned, "equipado": bool(user and cls._is_equipped(product, user)),
        }

    @classmethod
    def _purchase(cls, purchase, user=None):
        return {
            "id": purchase.id,
            "produto": cls._product(purchase.produto, user, {purchase.produto_id} if purchase.status == "concluida" else set()),
            "preco_edinhos": purchase.preco_edinhos, "status": purchase.status,
            "pode_reembolsar": purchase.status == "concluida" and bool(purchase.produto.reembolsavel),
            "created_at": purchase.created_at.isoformat() if purchase.created_at else None,
            "refunded_at": purchase.refunded_at.isoformat() if purchase.refunded_at else None,
        }

    @safe_route
    def catalog(self, token_data):
        self._ensure_catalog()
        user = db.session.get(Users, token_data["id"])
        owned_ids = {item.produto_id for item in MarketplacePurchase.query.filter_by(usuario_id=user.id, status="concluida").all()}
        products = MarketplaceProduct.query.filter_by(ativo=True).order_by(MarketplaceProduct.categoria, MarketplaceProduct.destaque.desc(), MarketplaceProduct.nome).all()
        return jsonify({
            "saldo_edinhos": self._balance(user.id),
            "produtos": [self._product(item, user, owned_ids) for item in products],
            "equipados": {
                "tema": user.tema or DEFAULT_THEME,
                "adorno": user.adorno_foto,
                "timo_skin": user.timo_skin or "default",
                "timo_cenario": user.timo_cenario or "workshop",
            },
        }), 200

    @safe_route
    def purchases(self, token_data):
        self._ensure_catalog()
        user = db.session.get(Users, token_data["id"])
        rows = MarketplacePurchase.query.filter_by(usuario_id=user.id).order_by(MarketplacePurchase.created_at.desc()).all()
        return jsonify({"saldo_edinhos": self._balance(user.id), "compras": [self._purchase(item, user) for item in rows]}), 200

    @safe_route
    def owned_adornments(self, token_data):
        """Lista somente adornos adquiridos pelo próprio usuário autenticado."""
        self._ensure_catalog()
        user = db.session.get(Users, token_data["id"])
        purchases = (
            MarketplacePurchase.query
            .join(MarketplaceProduct, MarketplaceProduct.id == MarketplacePurchase.produto_id)
            .filter(
                MarketplacePurchase.usuario_id == user.id,
                MarketplacePurchase.status == "concluida",
                MarketplaceProduct.categoria == "adorno",
                MarketplaceProduct.ativo.is_(True),
            )
            .order_by(MarketplacePurchase.created_at.desc())
            .all()
        )
        products = []
        seen = set()
        for purchase in purchases:
            if purchase.produto_id in seen:
                continue
            seen.add(purchase.produto_id)
            products.append(self._product(purchase.produto, user, {purchase.produto_id}))
        return jsonify({"adornos": products, "equipado": user.adorno_foto}), 200

    @safe_route
    def owned_scenarios(self, token_data):
        """Lista os cenários premium adquiridos pelo usuário autenticado."""
        self._ensure_catalog()
        user = db.session.get(Users, token_data["id"])
        purchases = (
            MarketplacePurchase.query
            .join(MarketplaceProduct, MarketplaceProduct.id == MarketplacePurchase.produto_id)
            .filter(
                MarketplacePurchase.usuario_id == user.id,
                MarketplacePurchase.status == "concluida",
                MarketplaceProduct.categoria == "timo_cenario",
                MarketplaceProduct.ativo.is_(True),
            )
            .order_by(MarketplacePurchase.created_at.desc())
            .all()
        )
        products = []
        seen = set()
        for purchase in purchases:
            if purchase.produto_id in seen:
                continue
            seen.add(purchase.produto_id)
            products.append(self._product(purchase.produto, user, {purchase.produto_id}))
        return jsonify({"cenarios": products, "equipado": user.timo_cenario or "workshop"}), 200

    @safe_route
    def checkout(self, token_data):
        self._ensure_catalog()
        body = request.get_json(silent=True) or {}
        raw_ids = body.get("produto_ids")
        if raw_ids is None:
            raw_ids = [body.get("produto_id")]
        if not isinstance(raw_ids, list) or not raw_ids or len(raw_ids) > 30:
            return jsonify("O carrinho deve conter entre 1 e 30 itens."), 400
        try:
            product_ids = list(dict.fromkeys(int(value) for value in raw_ids))
        except (TypeError, ValueError):
            return jsonify("O carrinho possui um produto inválido."), 400

        user = Users.query.filter_by(id=token_data["id"]).with_for_update().first()
        products = MarketplaceProduct.query.filter(MarketplaceProduct.id.in_(product_ids), MarketplaceProduct.ativo.is_(True)).all()
        products_by_id = {item.id: item for item in products}
        if len(products_by_id) != len(product_ids):
            return jsonify("Um ou mais produtos não estão disponíveis."), 404
        products = [products_by_id[item_id] for item_id in product_ids]
        active = MarketplacePurchase.query.filter(
            MarketplacePurchase.usuario_id == user.id,
            MarketplacePurchase.produto_id.in_(product_ids),
            MarketplacePurchase.status == "concluida",
        ).all()
        already_owned = {item.produto_id for item in active}
        duplicated = [item.nome for item in products if item.id in already_owned or item.codigo == "tema_tmhub"]
        if duplicated:
            return jsonify({"message": "Você já possui um ou mais itens do carrinho.", "itens": duplicated}), 409

        total = sum(max(0, int(item.preco_edinhos or 0)) for item in products)
        balance = self._balance(user.id)
        if balance < total:
            return jsonify({"message": "Saldo insuficiente.", "saldo_edinhos": balance, "necessario": total}), 409
        purchases = []
        for product in products:
            purchase = MarketplacePurchase(usuario_id=user.id, produto_id=product.id, preco_edinhos=product.preco_edinhos, status="concluida")
            db.session.add(purchase)
            purchases.append(purchase)
        if total:
            db.session.add(TMHubEdinhoLedger(usuario_id=user.id, tipo="marketplace_compra", quantidade=-total, descricao=f"Marketplace: {len(products)} item(ns)"))
        db.session.commit()
        return jsonify({
            "compras": [self._purchase(item, user) for item in purchases],
            "saldo_edinhos": self._balance(user.id), "total_edinhos": total,
        }), 201

    @safe_route
    def refund(self, token_data, purchase_id):
        user = Users.query.filter_by(id=token_data["id"]).with_for_update().first()
        purchase = MarketplacePurchase.query.filter_by(id=purchase_id, usuario_id=user.id).with_for_update().first()
        if not purchase:
            return jsonify("Compra não encontrada."), 404
        if purchase.status != "concluida":
            return jsonify("Essa compra já foi reembolsada."), 409
        if not purchase.produto.reembolsavel:
            return jsonify("Esse item não aceita reembolso."), 409
        purchase.status = "reembolsada"
        purchase.refunded_at = datetime.now()
        if purchase.produto.categoria == "tema" and self._is_equipped(purchase.produto, user):
            user.tema = DEFAULT_THEME
        if purchase.produto.categoria == "adorno" and self._is_equipped(purchase.produto, user):
            user.adorno_foto = None
        if purchase.produto.categoria == "timo_skin" and self._is_equipped(purchase.produto, user):
            user.timo_skin = "default"
        if purchase.produto.categoria == "timo_cenario" and self._is_equipped(purchase.produto, user):
            user.timo_cenario = "workshop"
        if purchase.preco_edinhos:
            db.session.add(TMHubEdinhoLedger(usuario_id=user.id, tipo="marketplace_reembolso", quantidade=purchase.preco_edinhos, descricao=f"Reembolso: {purchase.produto.nome} (compra {purchase.id})"))
        db.session.commit()
        return jsonify({"compra": self._purchase(purchase, user), "saldo_edinhos": self._balance(user.id)}), 200

    @safe_route
    def equip(self, token_data):
        body = request.get_json(silent=True) or {}
        category = str(body.get("categoria") or "").lower()
        if category not in {"tema", "adorno", "timo_skin", "timo_cenario"}:
            return jsonify("Selecione uma categoria de personalização válida."), 400
        user = Users.query.filter_by(id=token_data["id"]).with_for_update().first()
        product_id = body.get("produto_id")
        # Remover a personalização do próprio perfil é uma ação de conta e
        # continua disponível mesmo enquanto a loja está restrita aos admins.
        if product_id is None and category == "adorno":
            user.adorno_foto = None
            db.session.commit()
            return jsonify({"tema": user.tema or DEFAULT_THEME, "adorno": None, "timo_skin": user.timo_skin or "default"}), 200
        if product_id is None and category == "timo_skin":
            user.timo_skin = "default"
            db.session.commit()
            return jsonify({"tema": user.tema or DEFAULT_THEME, "adorno": user.adorno_foto, "timo_skin": "default"}), 200
        if product_id is None and category == "timo_cenario":
            user.timo_cenario = "workshop"
            db.session.commit()
            return jsonify({
                "tema": user.tema or DEFAULT_THEME,
                "adorno": user.adorno_foto,
                "timo_skin": user.timo_skin or "default",
                "timo_cenario": "workshop",
            }), 200
        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            return jsonify("Selecione um item válido."), 400
        product = MarketplaceProduct.query.filter_by(id=product_id, categoria=category, ativo=True).first()
        if not product:
            return jsonify("Personalização não encontrada."), 404
        owned = product.codigo == "tema_tmhub" or MarketplacePurchase.query.filter_by(usuario_id=user.id, produto_id=product.id, status="concluida").first() is not None
        if not owned:
            return jsonify("Adquira esse item antes de equipá-lo."), 403
        if category == "tema":
            user.tema = product.codigo.removeprefix("tema_")
        elif category == "adorno":
            user.adorno_foto = product.codigo
        elif category == "timo_skin":
            user.timo_skin = product.codigo
        else:
            user.timo_cenario = product.codigo.removeprefix("timo_cenario_")
        db.session.commit()
        return jsonify({
            "tema": user.tema or DEFAULT_THEME,
            "adorno": user.adorno_foto,
            "timo_skin": user.timo_skin or "default",
            "timo_cenario": user.timo_cenario or "workshop",
        }), 200
