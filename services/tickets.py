# Regras de negócio de chamados.
# Biblioteca padrão.
from datetime import datetime, timedelta, timezone
from secrets import choice
from pathlib import Path
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

# Dependências externas.
from flask import jsonify, request, send_from_directory
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError

# Módulos internos da aplicação.
from models.tc_comentarios import TicketComment
from models.tc_anexos import TicketAttachment
from models.tc_historico import Ticket
from models.tc_motivos import TicketReason
from models.setores import Sector
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
TICKET_UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads" / "tickets"
ATTACHMENT_MIME_TYPES = {
    "application/pdf": ".pdf", "image/png": ".png", "image/jpeg": ".jpg",
    "image/webp": ".webp", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
}
OLE_FILE_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
MAX_ATTACHMENT_IMAGE_PIXELS = 25_000_000


def _is_valid_attachment_content(file, content_type):
    """Confirma o conteúdo do arquivo antes de deixá-lo no disco."""
    try:
        if content_type == "application/pdf":
            return file.read(5) == b"%PDF-"
        if content_type.startswith("image/"):
            image = Image.open(file)
            width, height = image.size
            if not width or not height or width * height > MAX_ATTACHMENT_IMAGE_PIXELS:
                return False
            image.verify()
            return True
        if content_type == "application/vnd.ms-excel":
            return file.read(8) == OLE_FILE_SIGNATURE
        if content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            with ZipFile(file) as archive:
                return "[Content_Types].xml" in archive.namelist()
    except (BadZipFile, UnidentifiedImageError, OSError, ValueError):
        return False
    finally:
        file.seek(0)
    return False
TIMO_RESOLUTION_ORIGIN = "timo:ticket-resolution"
TIMO_USER = {
    "id": None,
    "nome": "Timo Bot",
    "email": None,
    "avatar_type": "timo",
}
TIMO_RESOLUTION_MESSAGES = (
    "Gotcha! Seu chamado foi atendido e finalizado com sucesso!\nMuito obrigado por participar de nosso projeto! ❤️🚀",
    "Tudo certo por aqui! Seu chamado foi concluído com sucesso.\nObrigado por construir o TM Hub com a gente! ✨",
    "Missão cumprida! A tratativa deste chamado foi finalizada.\nConte sempre com a gente. 🤖💚",
    "Chamado resolvido! Espero que agora esteja tudo fluindo por aí.\nObrigado pelo aviso e pela parceria! 🚀",
    "Prontinho! Finalizamos o atendimento deste chamado com sucesso.\nSeu feedback ajuda o TM Hub a evoluir. 💚",
    "Boas notícias: a solicitação foi atendida e encerrada!\nMuito obrigado por fazer parte do projeto. ✨",
    "Atendimento concluído com sucesso!\nSe precisar de algo mais, é só abrir um novo chamado. 🤝",
    "Tudo resolvido! Este chamado já recebeu a tratativa necessária.\nObrigado pela confiança no TM Hub. 💚",
    "Fechamos por aqui com sucesso!\nAgradecemos por registrar sua solicitação e ajudar a melhorar a operação. 🚀",
    "Chamado finalizado! Espero que a solução deixe seu dia um pouco mais leve.\nObrigado por estar com a gente. ✨",
)


def _now():
    return datetime.now(timezone.utc)


def _serialize_user(user):
    if not user:
        return None
    return {
        "id": user.id,
        "nome": user.nome,
        "email": user.email,
        "foto_perfil": user.foto_perfil,
    }


def _serialize_reason(reason):
    if not reason:
        return None
    result = {"id": reason.id, "nome": reason.nome, "ativo": bool(reason.ativo), "setor_id": reason.setor_id}
    # Se o relacionamento setor estiver carregado, inclui o nome
    if hasattr(reason, 'setor') and reason.setor:
        result["setor"] = {"id": reason.setor.id, "nome": reason.setor.nome}
    return result


def _serialize_branch(branch):
    if not branch:
        return None
    return {"id": branch.id, "nome": branch.nome}


def _serialize_attachment(attachment):
    """Expõe apenas os metadados necessários para buscar um anexo protegido."""
    return {
        "id": attachment.id,
        "filename": attachment.arquivo.split("__", 1)[-1],
        "type": attachment.tipo,
        "size": attachment.tamanho,
        "url": f"/tickets/{attachment.ticket_id}/anexos/{attachment.id}",
    }


def _protected_attachment_response(ticket, attachment, as_attachment):
    response = send_from_directory(
        TICKET_UPLOAD_DIR / str(ticket.id),
        attachment.arquivo,
        as_attachment=as_attachment,
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _validate_attachment_upload(file):
    """Valida o arquivo e prepara os metadados seguros para armazenamento."""
    if not file or not file.filename:
        raise ValueError("O arquivo está vazio.")
    if file.content_type not in ATTACHMENT_MIME_TYPES:
        raise ValueError("Tipo de arquivo não suportado. Use PDF, PNG, JPG, WebP, XLS ou XLSX.")

    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > 15 * 1024 * 1024:
        raise ValueError("O arquivo excede o limite de 15MB.")
    if not _is_valid_attachment_content(file, file.content_type):
        raise ValueError("O conteúdo do arquivo não corresponde ao tipo informado.")

    original_name = secure_filename(file.filename)
    if not original_name:
        raise ValueError("Nome de arquivo inválido.")
    display_name = f"{Path(original_name).stem}{ATTACHMENT_MIME_TYPES[file.content_type]}"
    return display_name, f"{uuid4().hex}__{display_name}", file_size


def _serialize_comment(comment, requester_id=None):
    is_timo = comment.descricao_origem == TIMO_RESOLUTION_ORIGIN
    return {
        "id": comment.id,
        "title": comment.titulo,
        "description": comment.descricao,
        "description_origin": comment.descricao_origem,
        "attachments": [
            _serialize_attachment(item)
            for item in TicketAttachment.query.filter_by(comentario_id=comment.id).all()
        ],
        "status": comment.status,
        "created_by": (
            _serialize_user(comment.criador)
            if is_timo and comment.criador
            else TIMO_USER if is_timo else _serialize_user(comment.criador)
        ),
        "is_requester": bool(
            not is_timo
            and requester_id is not None
            and comment.created_by == requester_id
        ),
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
        payload["attachments"] = [
            _serialize_attachment(item)
            for item in TicketAttachment.query.filter_by(ticket_id=ticket.id, comentario_id=None).all()
        ]
        payload["comments"] = [
            _serialize_comment(item, ticket.created_by)
            for item in ticket.comentarios
        ]
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
    def _add_timo_resolution_message(ticket):
        """Registra uma única despedida do Timo quando o chamado é resolvido."""
        already_sent = TicketComment.query.filter_by(
            ticket_id=ticket.id,
            descricao_origem=TIMO_RESOLUTION_ORIGIN,
        ).first()
        if already_sent:
            return None

        timo_user = Users.query.filter(
            db.func.lower(Users.nome) == "timo bot"
        ).first()
        comment = TicketComment(
            ticket_id=ticket.id,
            descricao=choice(TIMO_RESOLUTION_MESSAGES),
            descricao_origem=TIMO_RESOLUTION_ORIGIN,
            status="ENVIADO",
            created_by=timo_user.id if timo_user else None,
        )
        db.session.add(comment)
        return comment

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
        query = TicketReason.query.options(joinedload(TicketReason.setor))
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
        setor_id = (request.get_json(silent=True) or {}).get("setor_id")
        # Validar setor se informado
        if setor_id is not None:
            setor = db.session.get(Sector, setor_id)
            if not setor:
                return jsonify("Setor não encontrado."), 404
            if not setor.ativo:
                return jsonify("Setor está inativo."), 400
        reason = TicketReason(nome=name[:120], ativo=True, setor_id=setor_id)
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
        if "setor_id" in body:
            setor_id = body.get("setor_id")
            if setor_id is not None:
                setor = db.session.get(Sector, setor_id)
                if not setor:
                    return jsonify("Setor não encontrado."), 404
                reason.setor_id = setor.id
            else:
                reason.setor_id = None
        db.session.commit()
        return jsonify(_serialize_reason(reason))

    @safe_route
    def assignees(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem direcionar chamados."), 403
        term = str(request.args.get("q") or "").strip()
        setor_id = request.args.get("setor_id", type=int)
        try:
            limit = min(max(int(request.args.get("limit") or 50), 1), 100)
        except (TypeError, ValueError):
            limit = 50

        query = Users.query
        # Filtrar por setor se informado
        if setor_id is not None:
            query = query.filter(Users.setor_id == setor_id)
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
        is_multipart = request.mimetype == "multipart/form-data"
        body = request.form if is_multipart else request.get_json(silent=True) or {}
        name = str(body.get("name") or "").strip()
        observation = str(body.get("observation") or "").strip()
        if not name or not observation:
            return jsonify("Informe o título e a descrição do chamado."), 400
        try:
            reason_id = int(body["reason_id"]) if body.get("reason_id") not in (None, "") else None
            responsible_id = int(body["responsible_id"]) if body.get("responsible_id") not in (None, "") else None
        except (TypeError, ValueError):
            return jsonify("Motivo ou responsável do chamado inválido."), 400
        if reason_id is not None and not db.session.get(TicketReason, reason_id):
            return jsonify("Motivo do chamado não encontrado."), 404
        if responsible_id is not None and not is_admin(token_data):
            return jsonify("Apenas administradores podem direcionar chamados."), 403
        if responsible_id is not None and not db.session.get(Users, responsible_id):
            return jsonify("Responsável do chamado não encontrado."), 404
        
        # Validar setor: motivo e responsável devem ter o mesmo setor
        if reason_id is not None and responsible_id is not None:
            reason = db.session.get(TicketReason, reason_id)
            responsible = db.session.get(Users, responsible_id)
            if reason and responsible:
                # Permite setor_id nulo para compatibilidade
                if reason.setor_id is not None and responsible.setor_id is not None:
                    if reason.setor_id != responsible.setor_id:
                        return jsonify("O responsável não pertence ao setor do motivo."), 400
        
        branch_id = self._creation_branch_id(token_data)
        if not branch_id:
            return jsonify("Selecione uma única filial ativa antes de abrir o chamado."), 400

        uploaded_files = request.files.getlist("arquivos") if is_multipart else []
        prepared_files = []
        for file in uploaded_files:
            try:
                display_name, filename, file_size = _validate_attachment_upload(file)
            except ValueError as error:
                return jsonify(str(error)), 400
            prepared_files.append((file, display_name, filename, file_size))

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
        saved_paths = []
        try:
            if prepared_files:
                db.session.flush()
                upload_dir = TICKET_UPLOAD_DIR / str(ticket.id)
                upload_dir.mkdir(parents=True, exist_ok=True)
                for file, _display_name, filename, file_size in prepared_files:
                    filepath = upload_dir / filename
                    saved_paths.append(filepath)
                    file.save(filepath)
                    db.session.add(TicketAttachment(
                        ticket_id=ticket.id,
                        arquivo=filename,
                        tamanho=file_size,
                        tipo=file.content_type,
                        created_by=token_data["id"],
                    ))
            db.session.commit()
        except Exception:
            for filepath in saved_paths:
                if filepath.exists():
                    filepath.unlink()
            raise
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
            # Validar setor: se já houver responsável, verificar compatibilidade
            if ticket.responsible_id is not None:
                reason = db.session.get(TicketReason, reason_id)
                responsible = db.session.get(Users, ticket.responsible_id)
                if reason and responsible:
                    if reason.setor_id is not None and responsible.setor_id is not None:
                        if reason.setor_id != responsible.setor_id:
                            return jsonify("O responsável atual não pertence ao setor do novo motivo. Selecione um novo responsável."), 400
            ticket.motivo_id = reason_id
            changes.append("Motivo atualizado")
        if "responsible_id" in body:
            if not is_admin(token_data):
                return jsonify("Apenas administradores podem direcionar chamados."), 403
            responsible_id = body.get("responsible_id")
            if responsible_id is not None and not db.session.get(Users, responsible_id):
                return jsonify("Responsável do chamado não encontrado."), 404
            # Validar setor: responsável deve pertencer ao setor do motivo
            if ticket.motivo_id is not None:
                reason = db.session.get(TicketReason, ticket.motivo_id)
                responsible = db.session.get(Users, responsible_id)
                if reason and responsible:
                    if reason.setor_id is not None and responsible.setor_id is not None:
                        if reason.setor_id != responsible.setor_id:
                            return jsonify("O responsável não pertence ao setor do motivo."), 400
            ticket.responsible_id = responsible_id
            changes.append("Responsável atualizado")
        if "status" in body:
            status = str(body.get("status") or "").strip().upper()
            if status not in VALID_STATUSES:
                return jsonify("Status de chamado inválido."), 400
            was_resolved = ticket.status == "RESOLVIDO"
            ticket.status = status
            if status in FINAL_STATUSES:
                ticket.resolved_at = _now()
                ticket.resolved_by = token_data["id"]
            else:
                ticket.resolved_at = None
                ticket.resolved_by = None
            if status == "RESOLVIDO" and not was_resolved:
                self._add_timo_resolution_message(ticket)
            changes.append(f"Status alterado para {status}")
        if not changes:
            return jsonify("Nenhuma alteração válida foi informada."), 400
        ticket.updated_by = token_data["id"]
        db.session.commit()
        self._notify(ticket, "Chamado atualizado", ". ".join(changes) + ".")
        socketio.emit("ticket_update", {"action": "updated", "id": ticket.id, "status": ticket.status})
        return jsonify(_serialize_ticket(ticket, include_comments=True))

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
            created_by=token_data["id"],
        )
        db.session.add(comment)
        ticket.updated_by = token_data["id"]
        db.session.commit()
        self._notify(ticket, "Novo comentário", description)
        socketio.emit("ticket_update", {"action": "commented", "id": ticket.id, "comment_id": comment.id})
        return jsonify(_serialize_comment(comment, ticket.created_by)), 201

    @safe_route
    def upload_attachment(self, ticket_id, token_data, comment_id=None):
        """Upload de anexo em um chamado."""
        ticket = self._find_visible(ticket_id, token_data)
        if not ticket:
            return jsonify("Chamado não encontrado ou sem acesso."), 404
        denied = self._permission(token_data, "edit")
        if denied:
            return denied
        comment = None
        if comment_id is not None:
            comment = TicketComment.query.filter_by(id=comment_id, ticket_id=ticket.id).first()
            if not comment:
                return jsonify("Comentário não encontrado."), 404

        if "arquivo" not in request.files:
            return jsonify("Nenhum arquivo foi enviado."), 400

        file = request.files["arquivo"]
        try:
            display_name, filename, file_size = _validate_attachment_upload(file)
        except ValueError as error:
            return jsonify(str(error)), 400
        upload_dir = TICKET_UPLOAD_DIR / str(ticket_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        filepath = upload_dir / filename
        file.save(filepath)

        try:
            attachment = TicketAttachment(
                ticket_id=ticket.id,
                comentario_id=comment.id if comment else None,
                arquivo=filename,
                tamanho=file_size,
                tipo=file.content_type,
                created_by=token_data["id"]
            )
            db.session.add(attachment)
            db.session.commit()
        except Exception:
            if filepath.exists():
                filepath.unlink()
            raise

        self._notify(ticket, "Novo anexo", f"Arquivo '{display_name}' anexado ao chamado.")
        socketio.emit("ticket_update", {"action": "attachment_added", "id": ticket.id, "attachment_id": attachment.id})

        return jsonify({
            "message": "Anexo anexado com sucesso.",
            "attachment": {
                **_serialize_attachment(attachment),
                "created_at": attachment.created_at.isoformat(),
                "criador": _serialize_user(attachment.criador)
            }
        }), 201

    @safe_route
    def remove_attachment(self, ticket_id, attachment_id, token_data):
        """Remover anexo de um chamado."""
        denied = self._permission(token_data, "edit")
        if denied:
            return denied
        ticket = self._find_visible(ticket_id, token_data)
        if not ticket:
            return jsonify("Chamado não encontrado ou sem acesso."), 404

        attachment = TicketAttachment.query.filter_by(id=attachment_id, ticket_id=ticket_id).first()
        if not attachment:
            return jsonify("Anexo não encontrado."), 404

        # Remover arquivo do sistema
        filepath = TICKET_UPLOAD_DIR / str(ticket.id) / attachment.arquivo
        if filepath.exists():
            filepath.unlink()

        db.session.delete(attachment)
        db.session.commit()

        self._notify(ticket, "Anexo removido", f"Arquivo '{attachment.arquivo}' removido.")
        socketio.emit("ticket_update", {"action": "attachment_removed", "id": ticket.id, "attachment_id": attachment_id})

        return jsonify("Anexo removido com sucesso."), 200

    @safe_route
    def list_attachments(self, ticket_id, token_data):
        """Listar anexos de um chamado."""
        ticket = self._find_visible(ticket_id, token_data)
        if not ticket:
            return jsonify("Chamado não encontrado ou sem acesso."), 404

        attachments = TicketAttachment.query.filter_by(ticket_id=ticket_id).all()
        return jsonify([{
            **_serialize_attachment(attachment),
            "created_at": attachment.created_at.isoformat(),
            "created_by": _serialize_user(attachment.criador),
        } for attachment in attachments])

    @safe_route
    def get_attachment(self, ticket_id, filename, token_data):
        """Baixar anexo de um chamado."""
        ticket = self._find_visible(ticket_id, token_data)
        if not ticket:
            return jsonify("Chamado não encontrado ou sem acesso."), 404

        attachment = TicketAttachment.query.filter_by(ticket_id=ticket_id, arquivo=filename).first()
        if not attachment:
            return jsonify("Anexo não encontrado."), 404

        return _protected_attachment_response(ticket, attachment, as_attachment=True)

    @safe_route
    def get_attachment_by_id(self, ticket_id, attachment_id, token_data):
        ticket = self._find_visible(ticket_id, token_data)
        if not ticket:
            return jsonify("Chamado não encontrado ou sem acesso."), 404
        attachment = TicketAttachment.query.filter_by(id=attachment_id, ticket_id=ticket.id).first()
        if not attachment:
            return jsonify("Anexo não encontrado."), 404
        return _protected_attachment_response(ticket, attachment, as_attachment=False)

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
