# Regras de negócio de setores.
from flask import jsonify, request
from models.setores import Sector
from utils.db import db
from utils.safe_route import safe_route


def _text(value):
    return str(value or "").strip()


def _serialize_sector(sector):
    if not sector:
        return None
    return {
        "id": sector.id,
        "nome": sector.nome,
        "ativo": bool(sector.ativo),
    }


class SectorService:
    @safe_route
    def read(self, token_data):
        """Listar todos os setores."""
        include_inactive = str(request.args.get("include_inactive") or "").lower() in {"1", "true", "yes"}
        if include_inactive and not is_admin(token_data):
            return jsonify("Apenas administradores podem consultar setores inativos."), 403
        
        query = Sector.query
        if not include_inactive:
            query = query.filter_by(ativo=True)
        
        sectors = query.order_by(Sector.nome).all()
        return jsonify([_serialize_sector(s) for s in sectors])

    @safe_route
    def create(self, token_data):
        """Criar um novo setor."""
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem criar setores."), 403
        
        name = _text(request.get_json(silent=True) or {}).get("nome")
        if not name or len(name) < 2:
            return jsonify("Informe um nome válido para o setor."), 400
        
        duplicate = Sector.query.filter(db.func.lower(Sector.nome) == name.lower()).first()
        if duplicate:
            return jsonify("Este setor já está cadastrado."), 409
        
        sector = Sector(nome=name[:120], ativo=True)
        db.session.add(sector)
        db.session.commit()
        return jsonify(_serialize_sector(sector)), 201

    @safe_route
    def update(self, sector_id, token_data):
        """Atualizar um setor."""
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem alterar setores."), 403
        
        sector = db.session.get(Sector, sector_id)
        if not sector:
            return jsonify("Setor não encontrado."), 404
        
        body = request.get_json(silent=True) or {}
        if "nome" in body:
            name = _text(body.get("nome"))
            if not name or len(name) < 2:
                return jsonify("Informe um nome válido para o setor."), 400
            
            duplicate = Sector.query.filter(
                db.func.lower(Sector.nome) == name.lower(),
                Sector.id != sector.id,
            ).first()
            if duplicate:
                return jsonify("Este setor já está cadastrado."), 409
            
            sector.nome = name[:120]
        
        if "ativo" in body:
            sector.ativo = bool(body.get("ativo"))
        
        db.session.commit()
        return jsonify(_serialize_sector(sector))
