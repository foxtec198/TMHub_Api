from collections import defaultdict
from flask import jsonify, request as rq
from models.usuarios import Users
from models.pj_card import ProjectCard
from models.pj_card_member import ProjectCardMember
from models.pj_column import ProjectColumn
from models.pj_members import ProjectMember
from models.pj_projects import Project
from utils.db import db
from utils.safe_route import safe_route
from sqlalchemy import or_

DEFAULT_COLUMNS = ("A Fazer", "Em Andamento", "Concluido")

def _as_int(value):
    try: return int(value)
    except (TypeError, ValueError): return None

class ProjectService:
    def _serialize(self, project):
        members = (
            db.session.query(Users.id, Users.nome)
            .join(ProjectMember, ProjectMember.employee_id == Users.id)
            .filter(ProjectMember.project_id == project.id)
            .all()
        )
        members = [
            {
                "id": item.id,
                "nome": item.nome,
                "iniciais": self._initials(item.nome),
                "avatarColor": self._color(item.id),
            }
            for item in members
        ]

        columns = (
            ProjectColumn.query.filter_by(project_id=project.id)
            .order_by(ProjectColumn.ordem.asc())
            .all()
        )
        cards = (
            ProjectCard.query.filter(ProjectCard.column_id.in_([column.id for column in columns] or [0]))
            .order_by(ProjectCard.ordem.asc())
            .all()
        )
        card_members = (
            db.session.query(ProjectCardMember.card_id, Users.id, Users.nome)
            .join(Users, Users.id == ProjectCardMember.employee_id)
            .filter(ProjectCardMember.card_id.in_([card.id for card in cards] or [0]))
            .all()
        )

        members_by_card = defaultdict(list)
        for item in card_members:
            members_by_card[item.card_id].append(
                {
                    "id": item.id,
                    "nome": item.nome,
                    "iniciais": self._initials(item.nome),
                    "avatarColor": self._color(item.id),
                }
            )

        card_ids_by_column = defaultdict(list)
        cards_payload = {}
        cards_by_column = defaultdict(list)

        for card in cards:
            card_payload = {
                "id": card.id,
                "titulo": card.titulo,
                "descricao": card.descricao or "",
                "etiqueta": card.etiqueta,
                "memberIds": [member["id"] for member in members_by_card[card.id]],
                "members": members_by_card[card.id],
            }
            card_ids_by_column[card.column_id].append(card.id)
            cards_by_column[card.column_id].append(card_payload)
            cards_payload[card.id] = card_payload

        return {
            "id": project.id,
            "nome": project.nome,
            "cor": project.cor,
            "donoId": project.dono,
            "memberIds": [member["id"] for member in members],
            "members": members,
            "columns": [
                {
                    "id": column.id,
                    "titulo": column.titulo,
                    "cardIds": card_ids_by_column[column.id],
                    "cards": cards_by_column[column.id],
                }
                for column in columns
            ],
            "cards": cards_payload,
        }

    def _initials(self, name):
        parts = (name or "").split()
        return "".join([part[0] for part in parts[:2]]).upper() or "U"

    def _color(self, seed):
        colors = ["#7c5cff", "#22a3a3", "#e0763a", "#c14b6b", "#3d78c9", "#2f9e44"]
        return colors[int(seed or 0) % len(colors)]

    def _sync_members(self, project_id, member_ids):
        ProjectMember.query.filter_by(project_id=project_id).delete()
        for employee_id in sorted(set([item for item in member_ids if item is not None])):
            db.session.add(ProjectMember(project_id=project_id, employee_id=employee_id))

    def _sync_card_members(self, card_id, member_ids):
        ProjectCardMember.query.filter_by(card_id=card_id).delete()
        for employee_id in sorted(set([item for item in member_ids if item is not None])):
            db.session.add(ProjectCardMember(card_id=card_id, employee_id=employee_id))

    @safe_route
    def read(self, token_data):
        project_id = rq.args.get("id")
        user_id = _as_int(token_data.get("id"))
        member_project_ids = (
            db.session.query(ProjectMember.project_id)
            .filter(ProjectMember.employee_id == user_id)
        )
        query = Project.query.filter(
            or_(Project.dono == user_id, Project.id.in_(member_project_ids))
        )

        if project_id:
            query = query.filter_by(id=project_id)

        projects = query.order_by(Project.id.desc()).all()
        response = [self._serialize(project) for project in projects]

        if project_id:
            if not response:
                return jsonify("Projeto nao encontrado"), 404
            return jsonify(response[0]), 200

        return jsonify(response), 200

    @safe_route
    def create(self, token_data):
        body = rq.get_json() or {}
        nome = (body.get("nome") or "").strip()
        if not nome:
            return jsonify("Nome do projeto obrigatorio"), 400

        dono = _as_int(token_data.get("id"))
        if not dono:
            return jsonify("Usuario autenticado invalido"), 401
        project = Project(nome=nome, cor=body.get("cor") or "#7c5cff", dono=dono)
        db.session.add(project)
        db.session.flush()

        member_ids = [_as_int(item) for item in body.get("memberIds", [])]
        if dono:
            member_ids.append(dono)
        self._sync_members(project.id, member_ids)

        for ordem, title in enumerate(DEFAULT_COLUMNS):
            db.session.add(ProjectColumn(project_id=project.id, titulo=title, ordem=ordem))

        db.session.commit()
        return jsonify(self._serialize(project)), 201

    @safe_route
    def update(self, token_data):
        body = rq.get_json() or {}
        project_id = rq.args.get("id") or body.get("id")
        project = Project.query.filter_by(id=project_id).first()
        if not project:
            return jsonify("Projeto nao encontrado"), 404

        user_id = _as_int(token_data.get("id"))
        is_owner = project.dono == user_id
        is_member = ProjectMember.query.filter_by(project_id=project.id, employee_id=user_id).first() is not None
        if not is_owner and not is_member:
            return jsonify("Sem permissao para alterar este projeto"), 403

        if is_owner:
            if "nome" in body:
                project.nome = body["nome"]
            if "cor" in body:
                project.cor = body["cor"]
            if "memberIds" in body:
                member_ids = [_as_int(item) for item in body.get("memberIds", [])]
                member_ids.append(project.dono)
                self._sync_members(project.id, member_ids)
        if "columns" in body and "cards" in body:
            self._sync_board(project, body["columns"], body["cards"])

        db.session.commit()
        return jsonify(self._serialize(project)), 200

    @safe_route
    def delete(self, token_data):
        body = rq.get_json(silent=True) or {}
        project_id = rq.args.get("id") or body.get("id")
        project = Project.query.filter_by(id=project_id).first()
        if not project:
            return jsonify("Projeto nao encontrado"), 404

        user_id = _as_int(token_data.get("id"))
        if project.dono != user_id:
            return jsonify("Somente o dono pode excluir este projeto"), 403

        column_ids = [item.id for item in ProjectColumn.query.filter_by(project_id=project.id).all()]
        card_ids = [
            item.id for item in ProjectCard.query.filter(ProjectCard.column_id.in_(column_ids or [0])).all()
        ]

        ProjectCardMember.query.filter(ProjectCardMember.card_id.in_(card_ids or [0])).delete(synchronize_session=False)
        ProjectCard.query.filter(ProjectCard.id.in_(card_ids or [0])).delete(synchronize_session=False)
        ProjectColumn.query.filter(ProjectColumn.id.in_(column_ids or [0])).delete(synchronize_session=False)
        ProjectMember.query.filter_by(project_id=project.id).delete(synchronize_session=False)
        db.session.delete(project)
        db.session.commit()
        return jsonify("Projeto excluido"), 200

    def _sync_board(self, project, columns_payload, cards_payload):
        kept_column_ids = []
        kept_card_ids = []

        for column_order, column_payload in enumerate(columns_payload):
            column_id = _as_int(column_payload.get("id"))
            column = ProjectColumn.query.filter_by(id=column_id, project_id=project.id).first() if column_id else None
            if not column:
                column = ProjectColumn(project_id=project.id)
                db.session.add(column)
                db.session.flush()

            column.titulo = column_payload.get("titulo") or "Sem titulo"
            column.ordem = column_order
            kept_column_ids.append(column.id)

            for card_order, card_id in enumerate(column_payload.get("cardIds", [])):
                card_payload = cards_payload.get(str(card_id)) or cards_payload.get(card_id)
                if not card_payload:
                    continue

                numeric_card_id = _as_int(card_payload.get("id"))
                card = ProjectCard.query.filter_by(id=numeric_card_id).first() if numeric_card_id else None
                if not card:
                    card = ProjectCard()
                    db.session.add(card)
                    db.session.flush()

                card.column_id = column.id
                card.titulo = card_payload.get("titulo") or "Sem titulo"
                card.descricao = card_payload.get("descricao") or ""
                card.etiqueta = card_payload.get("etiqueta")
                card.ordem = card_order
                kept_card_ids.append(card.id)
                self._sync_card_members(card.id, [_as_int(item) for item in card_payload.get("memberIds", [])])

        old_cards = (
            ProjectCard.query.join(ProjectColumn, ProjectColumn.id == ProjectCard.column_id)
            .filter(ProjectColumn.project_id == project.id)
            .filter(ProjectCard.id.notin_(kept_card_ids or [0]))
            .all()
        )
        for card in old_cards:
            ProjectCardMember.query.filter_by(card_id=card.id).delete()
            db.session.delete(card)

        old_columns = (
            ProjectColumn.query.filter_by(project_id=project.id)
            .filter(ProjectColumn.id.notin_(kept_column_ids or [0]))
            .all()
        )
        for column in old_columns:
            db.session.delete(column)

    @safe_route
    def create_card(self, project_id, token_data):
        body = rq.get_json() or {}
        user_id = _as_int(token_data.get("id"))
        project = Project.query.filter_by(id=project_id).first()
        is_member = ProjectMember.query.filter_by(project_id=project_id, employee_id=user_id).first() is not None
        if not project or (project.dono != user_id and not is_member):
            return jsonify("Sem permissao para criar cards neste projeto"), 403
        column_id = _as_int(body.get("columnId") or body.get("column_id"))
        column = ProjectColumn.query.filter_by(id=column_id, project_id=project_id).first()
        if not column:
            return jsonify("Coluna nao encontrada"), 404

        title = (body.get("titulo") or "").strip()
        if not title:
            return jsonify("Titulo do card obrigatorio"), 400

        order = ProjectCard.query.filter_by(column_id=column.id).count()
        card = ProjectCard(
            column_id=column.id,
            titulo=title,
            descricao=body.get("descricao") or "",
            etiqueta=body.get("etiqueta"),
            ordem=order,
        )
        db.session.add(card)
        db.session.flush()
        self._sync_card_members(card.id, [_as_int(item) for item in body.get("memberIds", [])])
        db.session.commit()
        return jsonify(self._serialize(Project.query.filter_by(id=project_id).first())), 201

    @safe_route
    def update_card(self, card_id, token_data):
        card = ProjectCard.query.filter_by(id=card_id).first()
        if not card:
            return jsonify("Card nao encontrado"), 404

        project = (
            Project.query.join(ProjectColumn, ProjectColumn.project_id == Project.id)
            .filter(ProjectColumn.id == card.column_id)
            .first()
        )
        user_id = _as_int(token_data.get("id"))
        is_member = ProjectMember.query.filter_by(project_id=project.id, employee_id=user_id).first() is not None
        if project.dono != user_id and not is_member:
            return jsonify("Sem permissao para alterar cards neste projeto"), 403

        body = rq.get_json() or {}
        if "titulo" in body:
            card.titulo = body["titulo"]
        if "descricao" in body:
            card.descricao = body["descricao"] or ""
        if "etiqueta" in body:
            card.etiqueta = body["etiqueta"]
        if "memberIds" in body:
            self._sync_card_members(card.id, [_as_int(item) for item in body["memberIds"]])

        db.session.commit()
        return jsonify(self._serialize(project)), 200

    @safe_route
    def delete_card(self, card_id, token_data):
        card = ProjectCard.query.filter_by(id=card_id).first()
        if not card:
            return jsonify("Card nao encontrado"), 404

        project = (
            Project.query.join(ProjectColumn, ProjectColumn.project_id == Project.id)
            .filter(ProjectColumn.id == card.column_id)
            .first()
        )
        user_id = _as_int(token_data.get("id"))
        is_member = ProjectMember.query.filter_by(project_id=project.id, employee_id=user_id).first() is not None
        if project.dono != user_id and not is_member:
            return jsonify("Sem permissao para excluir cards neste projeto"), 403
        ProjectCardMember.query.filter_by(card_id=card.id).delete()
        db.session.delete(card)
        db.session.commit()
        return jsonify(self._serialize(project)), 200
