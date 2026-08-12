from datetime import datetime, timedelta, timezone

from flask import jsonify, request
from sqlalchemy import or_

from models.tc_comentarios import TicketComment
from models.tc_historico import Ticket
from models.tc_motivos import TicketReason
from models.filiais import Branch
from models.usuarios import Users
from utils.db import db
from utils.filial_scope import is_admin, is_matrix_user, requested_branch_ids
from utils.permissions import has_permission
from utils.safe_route import safe_route
from utils.socket import socketio
from utils.ticket_notifications import notify_ticket_recipients, send_ticket_test_email


SCREEN = "tickets"
OPEN_STATUSES = {"ABERTO", "EM_ANDAMENTO", "ATRASADO"}
FINAL_STATUSES = {"RESOLVIDO", "FECHADO", "CANCELADO"}
VALID_STATUSES = OPEN_STATUSES | FINAL_STATUSES
SLA = timedelta(days=1)


def _now():
    return datetime.now(timezone.utc)


def _serialize_user(user):
    if not user:
        return None
    return {"id": user.id, "nome": user.nome, "email": user.email}


def _serialize_reason(reason):
    if not reason:
        return None
    return {"id": reason.id, "nome": reason.nome, "ativo": bool(reason.ativo)}


def _serialize_branch(branch):
    if not branch:
        return None
    return {"id": branch.id, "nome": branch.nome}


def _serialize_comment(comment):
    return {
        "id": comment.id,
        "title": comment.titulo,
        "description": comment.descricao,
        "description_origin": comment.descricao_origem,
        "file": comment.arquivo,
        "status": comment.status,
        "created_by": _serialize_user(comment.criador),
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
        "read_at": comment.read_at.isoformat() if comment.read_at else None,
        "read_by_id": comment.read_by,
    }


def _ticket_due_at(ticket):
    if not ticket.created_at:
        return None
    created_at = ticket.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at + SLA


def _serialize_ticket(ticket, include_comments=False):
    due_at = _ticket_due_at(ticket)
    payload = {
        "id": ticket.id,
        "name": ticket.nome,
        "status": ticket.status,
        "observation": ticket.observacao,
        "reason": _serialize_reason(ticket.motivo),
        "created_by": _serialize_user(ticket.criador),
        "updated_by_id": ticket.updated_by,
        "resolved_by": _serialize_user(ticket.resolvido_por),
        "responsible": _serialize_user(ticket.responsavel),
        "branch": _serialize_branch(ticket.filial),
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        "due_at": due_at.isoformat() if due_at else None,
        "overdue": ticket.status == "ATRASADO",
    }
    if include_comments:
        payload["comments"] = [_serialize_comment(item) for item in ticket.comentarios]
    return payload


class TicketService:
    @staticmethod
    def _permission(token_data, action):
        if has_permission(token_data, SCREEN, action):
            return None
        return jsonify("Você não possui permissão para esta operação em chamados."), 403

    @staticmethod
    def _visible_query(token_data):
        query = Ticket.query
        requested_ids = requested_branch_ids()
        if is_admin(token_data):
            if requested_ids is not None:
                return query.filter(Ticket.filial_id.in_(requested_ids))
            return query
        user = db.session.get(Users, token_data["id"])
        branch_ids = {branch.id for branch in (user.filiais if user else []) if branch.ativa}
        if not branch_ids:
            return query.filter(db.false())
        return query.filter(
            Ticket.filial_id.in_(branch_ids),
            or_(Ticket.created_by == user.id, Ticket.responsible_id == user.id),
        )

    @staticmethod
    def _creation_branch_id(token_data):
        user = db.session.get(Users, token_data["id"])
        selected_ids = requested_branch_ids()

        if selected_ids is not None:
            active_selected = {
                branch.id
                for branch in Branch.query.filter(
                    Branch.id.in_(selected_ids),
                    Branch.ativa.is_(True),
                ).all()
            }
            if len(active_selected) == 1 and (
                is_admin(token_data)
                or is_matrix_user(token_data)
                or active_selected.issubset({branch.id for branch in (user.filiais if user else [])})
            ):
                return next(iter(active_selected))

        user_branch_ids = [
            branch.id for branch in (user.filiais if user else []) if branch.ativa
        ]
        return user_branch_ids[0] if len(user_branch_ids) == 1 else None

    @staticmethod
    def _find_visible(ticket_id, token_data):
        return TicketService._visible_query(token_data).filter(Ticket.id == ticket_id).first()

    @staticmethod
    def _recipient_emails(ticket):
        return {
            user.email
            for user in (ticket.criador, ticket.responsavel)
            if user and user.email
        }

    @staticmethod
    def _notify(ticket, title, detail):
        due_at = _ticket_due_at(ticket)
        notify_ticket_recipients(
            TicketService._recipient_emails(ticket),
            f"[Ticket #{ticket.id}] {title}",
            "\n".join(
                [
                    f"Chamado: {ticket.nome}",
                    f"Status: {ticket.status}",
                    f"Prazo: {due_at.strftime('%d/%m/%Y %H:%M') if due_at else 'não definido'}",
                    "",
                    detail,
                ]
            ),
        )

    @staticmethod
    def _refresh_overdue():
        deadline = _now() - SLA
        changed = (
            Ticket.query.filter(
                Ticket.status.in_(["ABERTO", "EM_ANDAMENTO"]),
                Ticket.created_at <= deadline,
            ).all()
        )
        if not changed:
            return []
        for ticket in changed:
            ticket.status = "ATRASADO"
        db.session.commit()
        for ticket in changed:
            TicketService._notify(ticket, "Chamado em atraso", "O prazo padrão de um dia foi excedido.")
        socketio.emit("ticket_update", {"action": "overdue", "ids": [item.id for item in changed]})
        return changed

    @safe_route
    def reasons(self, token_data):
        denied = self._permission(token_data, "view")
        if denied:
            return denied
        include_inactive = str(request.args.get("include_inactive") or "").lower() in {"1", "true", "yes"}
        if include_inactive and not is_admin(token_data):
            return jsonify("Apenas administradores podem consultar motivos inativos."), 403
        query = TicketReason.query
        if not include_inactive:
            query = query.filter_by(ativo=True)
        reasons = query.order_by(TicketReason.nome).all()
        return jsonify([_serialize_reason(item) for item in reasons])

    @safe_route
    def create_reason(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem criar motivos."), 403
        name = str((request.get_json(silent=True) or {}).get("nome") or "").strip()
        if len(name) < 2:
            return jsonify("Informe um motivo com ao menos 2 caracteres."), 400
        duplicate = TicketReason.query.filter(db.func.lower(TicketReason.nome) == name.lower()).first()
        if duplicate:
            return jsonify("Esse motivo já está cadastrado."), 409
        reason = TicketReason(nome=name[:120], ativo=True)
        db.session.add(reason)
        db.session.commit()
        return jsonify(_serialize_reason(reason)), 201

    @safe_route
    def update_reason(self, reason_id, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem alterar motivos."), 403
        reason = db.session.get(TicketReason, reason_id)
        if not reason:
            return jsonify("Motivo não encontrado."), 404
        body = request.get_json(silent=True) or {}
        if "nome" in body:
            name = str(body.get("nome") or "").strip()
            duplicate = TicketReason.query.filter(
                db.func.lower(TicketReason.nome) == name.lower(),
                TicketReason.id != reason.id,
            ).first()
            if len(name) < 2 or duplicate:
                return jsonify("Informe um motivo válido e não repetido."), 400
            reason.nome = name[:120]
        if "ativo" in body:
            reason.ativo = bool(body.get("ativo"))
        db.session.commit()
        return jsonify(_serialize_reason(reason))

    @safe_route
    def assignees(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem direcionar chamados."), 403
        term = str(request.args.get("q") or "").strip()
        try:
            limit = min(max(int(request.args.get("limit") or 50), 1), 100)
        except (TypeError, ValueError):
            limit = 50

        query = Users.query
        if term:
            pattern = f"%{term}%"
            query = query.filter(or_(Users.nome.ilike(pattern), Users.email.ilike(pattern)))
        users = query.order_by(Users.nome).limit(limit).all()
        return jsonify([_serialize_user(user) for user in users])

    @safe_route
    def read(self, token_data):
        denied = self._permission(token_data, "view")
        if denied:
            return denied
        self._refresh_overdue()
        query = self._visible_query(token_data).order_by(Ticket.created_at.desc())
        status = str(request.args.get("status") or "").strip().upper()
        if status in VALID_STATUSES:
            query = query.filter(Ticket.status == status)
        return jsonify([_serialize_ticket(ticket) for ticket in query.all()])

    @safe_route
    def detail(self, ticket_id, token_data):
        denied = self._permission(token_data, "view")
        if denied:
            return denied
        self._refresh_overdue()
        ticket = self._find_visible(ticket_id, token_data)
        if not ticket:
            return jsonify("Chamado não encontrado ou sem acesso."), 404
        return jsonify(_serialize_ticket(ticket, include_comments=True))

    @safe_route
    def create(self, token_data):
        denied = self._permission(token_data, "create")
        if denied:
            return denied
        body = request.get_json(silent=True) or {}
        name = str(body.get("name") or "").strip()
        observation = str(body.get("observation") or "").strip()
        if not name or not observation:
            return jsonify("Informe o título e a descrição do chamado."), 400
        reason_id = body.get("reason_id")
        if reason_id is not None and not db.session.get(TicketReason, reason_id):
            return jsonify("Motivo do chamado não encontrado."), 404
        responsible_id = body.get("responsible_id")
        if responsible_id is not None and not is_admin(token_data):
            return jsonify("Apenas administradores podem direcionar chamados."), 403
        if responsible_id is not None and not db.session.get(Users, responsible_id):
            return jsonify("Responsável do chamado não encontrado."), 404
        branch_id = self._creation_branch_id(token_data)
        if not branch_id:
            return jsonify("Selecione uma única filial ativa antes de abrir o chamado."), 400
        ticket = Ticket(
            nome=name[:180],
            observacao=observation,
            motivo_id=reason_id,
            created_by=token_data["id"],
            updated_by=token_data["id"],
            responsible_id=responsible_id,
            filial_id=branch_id,
        )
        db.session.add(ticket)
        db.session.commit()
        self._notify(ticket, "Novo chamado aberto", "Um novo chamado foi registrado e está aguardando tratativa.")
        socketio.emit("ticket_update", {"action": "created", "id": ticket.id})
        return jsonify(_serialize_ticket(ticket)), 201

    @safe_route
    def update(self, ticket_id, token_data):
        denied = self._permission(token_data, "edit")
        if denied:
            return denied
        ticket = self._find_visible(ticket_id, token_data)
        if not ticket:
            return jsonify("Chamado não encontrado ou sem acesso."), 404
        body = request.get_json(silent=True) or {}
        changes = []
        if "name" in body:
            name = str(body.get("name") or "").strip()
            if not name:
                return jsonify("Informe o título do chamado."), 400
            ticket.nome = name[:180]
            changes.append("Título atualizado")
        if "observation" in body:
            observation = str(body.get("observation") or "").strip()
            if not observation:
                return jsonify("Informe a descrição do chamado."), 400
            ticket.observacao = observation
            changes.append("Descrição atualizada")
        if "reason_id" in body:
            reason_id = body.get("reason_id")
            if reason_id is not None and not db.session.get(TicketReason, reason_id):
                return jsonify("Motivo do chamado não encontrado."), 404
            ticket.motivo_id = reason_id
            changes.append("Motivo atualizado")
        if "responsible_id" in body:
            if not is_admin(token_data):
                return jsonify("Apenas administradores podem direcionar chamados."), 403
            responsible_id = body.get("responsible_id")
            if responsible_id is not None and not db.session.get(Users, responsible_id):
                return jsonify("Responsável do chamado não encontrado."), 404
            ticket.responsible_id = responsible_id
            changes.append("Responsável atualizado")
        if "status" in body:
            status = str(body.get("status") or "").strip().upper()
            if status not in VALID_STATUSES:
                return jsonify("Status de chamado inválido."), 400
            ticket.status = status
            if status in FINAL_STATUSES:
                ticket.resolved_at = _now()
                ticket.resolved_by = token_data["id"]
            else:
                ticket.resolved_at = None
                ticket.resolved_by = None
            changes.append(f"Status alterado para {status}")
        if not changes:
            return jsonify("Nenhuma alteração válida foi informada."), 400
        ticket.updated_by = token_data["id"]
        db.session.commit()
        self._notify(ticket, "Chamado atualizado", ". ".join(changes) + ".")
        socketio.emit("ticket_update", {"action": "updated", "id": ticket.id, "status": ticket.status})
        return jsonify(_serialize_ticket(ticket))

    @safe_route
    def add_comment(self, ticket_id, token_data):
        denied = self._permission(token_data, "edit")
        if denied:
            return denied
        ticket = self._find_visible(ticket_id, token_data)
        if not ticket:
            return jsonify("Chamado não encontrado ou sem acesso."), 404
        body = request.get_json(silent=True) or {}
        description = str(body.get("description") or "").strip()
        if not description:
            return jsonify("Informe o conteúdo do comentário."), 400
        comment = TicketComment(
            ticket_id=ticket.id,
            titulo=str(body.get("title") or "").strip()[:180] or None,
            descricao=description,
            descricao_origem=str(body.get("description_origin") or "").strip() or None,
            arquivo=str(body.get("file") or "").strip()[:500] or None,
            created_by=token_data["id"],
        )
        db.session.add(comment)
        ticket.updated_by = token_data["id"]
        db.session.commit()
        self._notify(ticket, "Novo comentário", description)
        socketio.emit("ticket_update", {"action": "commented", "id": ticket.id, "comment_id": comment.id})
        return jsonify(_serialize_comment(comment)), 201

    @safe_route
    def test_email(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem testar o SMTP de chamados."), 403
        body = request.get_json(silent=True) or {}
        recipient = str(body.get("recipient") or "foxtec198@gmail.com").strip().lower()
        if recipient != "foxtec198@gmail.com":
            return jsonify("O e-mail de teste autorizado é foxtec198@gmail.com."), 400
        try:
            send_ticket_test_email(recipient)
        except Exception as error:
            return jsonify(f"Falha no SMTP: {error}"), 503
        return jsonify("E-mail de teste enviado com sucesso."), 200
