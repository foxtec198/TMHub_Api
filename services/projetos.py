from collections import defaultdict
from datetime import datetime as dt
from os import getenv
from pathlib import Path
from uuid import uuid4

from flask import current_app, jsonify, request as rq, send_from_directory
from werkzeug.utils import secure_filename
from models.usuarios import Users
from models.pj_card import ProjectCard
from models.pj_card_comment import ProjectCardComment
from models.pj_card_file import ProjectCardFile
from models.pj_card_member import ProjectCardMember
from models.pj_column import ProjectColumn
from models.pj_members import ProjectMember
from models.pj_projects import Project
from utils.db import db
from utils.safe_route import safe_route
from utils.permissions import has_permission
from utils.project_notifications import notify_card_members
from sqlalchemy import or_

DEFAULT_COLUMNS = ("A Fazer", "Em Andamento", "Concluido")
PROJECT_FILES_DIR = Path(
    getenv("PROJECT_FILES_DIR")
    or Path(__file__).resolve().parents[1] / "storage" / "project_cards"
)
MAX_PROJECT_FILE_SIZE = 15 * 1024 * 1024
ALLOWED_PROJECT_FILE_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx",
    ".xls", ".xlsx", ".csv", ".txt", ".zip",
}

def _as_int(value):
    try: return int(value)
    except (TypeError, ValueError): return None


def _arg_values(name):
    """Normaliza parâmetros repetidos ou separados por vírgula dos MultiSelects."""
    values = []
    for raw in rq.args.getlist(name):
        values.extend(value.strip() for value in str(raw).split(",") if value.strip())
    return values


def _parse_datetime(value):
    if value in (None, ""):
        return None
    try:
        parsed = dt.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone() if parsed.tzinfo else parsed.replace(tzinfo=dt.now().astimezone().tzinfo)
    except ValueError:
        raise ValueError("Informe uma data válida para o card.")

class ProjectService:
    @staticmethod
    def _is_admin(user_id):
        user = db.session.get(Users, user_id)
        return bool(user and str(user.role or "").upper() == "ADMIN")

    @staticmethod
    def _visible_project_ids(user_id, is_admin=False):
        if is_admin:
            return [row[0] for row in db.session.query(Project.id).all()]

        return [
            row[0]
            for row in db.session.query(Project.id).filter(
                or_(
                    Project.dono == user_id,
                    Project.id.in_(
                        db.session.query(ProjectMember.project_id).filter(
                            ProjectMember.employee_id == user_id
                        )
                    ),
                )
            ).all()
        ]

    @safe_route
    def dashboard(self, token_data):
        if not has_permission(token_data, "dashboard_projetos", "view"):
            return jsonify("Você não possui acesso ao Dashboard de Projetos."), 403
        user_id = _as_int(token_data.get("id"))
        project_ids = self._visible_project_ids(user_id, self._is_admin(user_id))
        project_filter = {_as_int(value) for value in _arg_values("projeto")} - {None}
        collaborator_filter = {_as_int(value) for value in _arg_values("colaborador")} - {None}
        card_filter = {_as_int(value) for value in _arg_values("card")} - {None}
        status_filter = {value.casefold() for value in _arg_values("status")}
        start = _parse_datetime(rq.args.get("inicio")) if rq.args.get("inicio") else None
        end = _parse_datetime(rq.args.get("fim")) if rq.args.get("fim") else None
        if end and end.hour == 0 and end.minute == 0 and end.second == 0:
            end = end.replace(hour=23, minute=59, second=59, microsecond=999999)

        columns = ProjectColumn.query.filter(ProjectColumn.project_id.in_(project_ids or [0])).all()
        column_project = {column.id: column.project_id for column in columns}
        column_status = {column.id: (column.titulo or "").casefold() for column in columns}
        cards = ProjectCard.query.filter(ProjectCard.column_id.in_(column_project or [0])).all()
        if project_filter:
            cards = [card for card in cards if column_project.get(card.column_id) in project_filter]
        card_members = defaultdict(list)
        for row in ProjectCardMember.query.filter(ProjectCardMember.card_id.in_([card.id for card in cards] or [0])).all():
            card_members[row.card_id].append(row.employee_id)
        now = dt.now().astimezone()
        filtered = []
        for card in cards:
            status = column_status.get(card.column_id, "")
            is_done = "conclu" in status
            if card_filter and card.id not in card_filter:
                continue
            if collaborator_filter and not collaborator_filter.intersection(card_members[card.id]):
                continue
            if status_filter and not any(value in status for value in status_filter):
                continue
            reference = card.data_inicio or card.created_at
            if start and (not reference or reference < start):
                continue
            if end and (not reference or reference > end):
                continue
            filtered.append((card, is_done))

        total = len(filtered)
        completed = [(card, done) for card, done in filtered if done]
        overdue = [(card, done) for card, done in filtered if not done and card.data_fim and card.data_fim < now]
        on_time = [(card, done) for card, done in filtered if not done and (not card.data_fim or card.data_fim >= now)]
        completed_on_time = [
            (card, done) for card, done in completed
            if not card.data_fim or (card.concluida_em and card.concluida_em <= card.data_fim)
        ]
        completed_late = [
            (card, done) for card, done in completed
            if card.data_fim and card.concluida_em and card.concluida_em > card.data_fim
        ]
        duration_rows = [
            (card.concluida_em - (card.data_inicio or card.created_at)).total_seconds() / 3600
            for card, _ in completed
            if card.concluida_em and (card.data_inicio or card.created_at)
        ]
        projects_query = Project.query.filter(Project.id.in_(project_ids or [0]))
        if project_filter:
            projects_query = projects_query.filter(Project.id.in_(project_filter))
        projects = projects_query.order_by(Project.nome.asc()).all()
        project_map = {project.id: project for project in projects}
        project_member_rows = ProjectMember.query.filter(
            ProjectMember.project_id.in_(project_map or [0])
        ).all()
        participant_ids = {
            row.employee_id for row in project_member_rows if row.employee_id
        }
        assigned_ids = {
            member
            for card, _ in filtered
            for member in card_members[card.id]
        }
        employee_rows = Users.query.filter(
            Users.id.in_(participant_ids | assigned_ids or {0})
        ).all()
        employees = {employee.id: employee.nome for employee in employee_rows}
        project_members = defaultdict(list)
        for row in project_member_rows:
            employee = next(
                (item for item in employee_rows if item.id == row.employee_id),
                None,
            )
            if not employee:
                continue
            project_members[row.project_id].append({
                "id": employee.id,
                "nome": employee.nome,
                "iniciais": self._initials(employee.nome),
                "avatarColor": self._color(employee.id),
            })
        by_employee = defaultdict(lambda: {"cards": 0, "concluidos": 0, "horas_execucao": []})
        for card, done in filtered:
            hours = None
            if done and card.concluida_em and (card.data_inicio or card.created_at):
                hours = round((card.concluida_em - (card.data_inicio or card.created_at)).total_seconds() / 3600, 2)
            for member_id in card_members[card.id]:
                by_employee[member_id]["cards"] += 1
                by_employee[member_id]["concluidos"] += int(done)
                if hours is not None:
                    by_employee[member_id]["horas_execucao"].append(hours)
        project_cards = defaultdict(list)
        for card, done in filtered:
            project_cards[column_project[card.column_id]].append((card, done))
        project_rows = []
        for project in projects:
            rows = project_cards.get(project.id, [])
            project_rows.append({
                "id": project.id,
                "nome": project.nome,
                "cor": project.cor,
                "cards": len(rows),
                "participantes": len(project_members[project.id]),
                "atrasado": any(not done and card.data_fim and card.data_fim < now for card, done in rows),
            })
        status_counts = {"abertas": 0, "andamento": 0, "concluidas": 0}
        within_deadline = 0
        outside_deadline = 0
        timeline_rows = []
        for card, done in filtered:
            status = column_status.get(card.column_id, "")
            if done:
                status_key = "concluida"
                status_counts["concluidas"] += 1
            elif "andamento" in status or "progresso" in status:
                status_key = "andamento"
                status_counts["andamento"] += 1
            else:
                status_key = "aberta"
                status_counts["abertas"] += 1

            is_outside = bool(
                card.data_fim
                and (
                    (done and card.concluida_em and card.concluida_em > card.data_fim)
                    or (not done and card.data_fim < now)
                )
            )
            outside_deadline += int(is_outside)
            within_deadline += int(not is_outside)
            project = project_map.get(column_project.get(card.column_id))
            timeline_rows.append({
                "id": card.id,
                "titulo": card.titulo,
                "projeto": project.nome if project else "Projeto removido",
                "status": status_key,
                "data_inicio": card.data_inicio.isoformat() if card.data_inicio else None,
                "data_fim": card.data_fim.isoformat() if card.data_fim else None,
                "concluida_em": card.concluida_em.isoformat() if card.concluida_em else None,
                "membros": [
                    {
                        "id": member_id,
                        "nome": employees.get(member_id, "Colaborador removido"),
                        "iniciais": self._initials(employees.get(member_id, "?")),
                        "avatarColor": self._color(member_id),
                    }
                    for member_id in card_members[card.id]
                ],
            })
        timeline_rows.sort(
            key=lambda row: row["data_inicio"] or row["data_fim"] or "9999"
        )
        return jsonify({
            "resumo": {
                "projetos": len(project_rows), "cards": total, "abertos": total - len(completed),
                "concluidos": len(completed), "atrasados": len(overdue), "no_prazo": len(on_time),
                "concluidos_no_prazo": len(completed_on_time), "concluidos_atraso": len(completed_late),
                "projetos_atrasados": sum(1 for row in project_rows if row["atrasado"]),
                "projetos_no_prazo": sum(1 for row in project_rows if not row["atrasado"]),
                "percentual_conclusao": round((len(completed) / total * 100) if total else 0, 1),
                "tempo_medio_horas": round(sum(duration_rows) / len(duration_rows), 2) if duration_rows else None,
                "participantes": len(participant_ids),
                "status_abertas": status_counts["abertas"],
                "status_andamento": status_counts["andamento"],
                "status_concluidas": status_counts["concluidas"],
                "dentro_prazo": within_deadline,
                "fora_prazo": outside_deadline,
                "percentual_dentro_prazo": round((within_deadline / total * 100) if total else 0, 1),
                "percentual_fora_prazo": round((outside_deadline / total * 100) if total else 0, 1),
            },
            "performance_colaboradores": [
                {"colaborador_id": member_id, "colaborador": employees.get(member_id, "Colaborador removido"),
                 "cards": data["cards"], "concluidos": data["concluidos"],
                 "tempo_medio_horas": round(sum(data["horas_execucao"]) / len(data["horas_execucao"]), 2) if data["horas_execucao"] else None}
                for member_id, data in by_employee.items()
            ],
            "cards": [
                {"id": card.id, "titulo": card.titulo, "projeto": project_map.get(column_project[card.column_id]).nome if project_map.get(column_project[card.column_id]) else None,
                 "data_inicio": card.data_inicio.isoformat() if card.data_inicio else None,
                 "data_fim": card.data_fim.isoformat() if card.data_fim else None,
                 "concluida_em": card.concluida_em.isoformat() if card.concluida_em else None,
                 "atrasado": (card, done) in overdue,
                 "atraso_horas": round((now - card.data_fim).total_seconds() / 3600, 2) if not done and card.data_fim and card.data_fim < now else 0,
                 "tempo_execucao_horas": round((card.concluida_em - (card.data_inicio or card.created_at)).total_seconds() / 3600, 2) if card.concluida_em and (card.data_inicio or card.created_at) else None}
                for card, done in filtered
            ],
            "projetos": project_rows,
            "participantes_por_projeto": [
                {
                    "projeto_id": project.id,
                    "projeto": project.nome,
                    "cor": project.cor,
                    "membros": project_members[project.id],
                }
                for project in projects
                if project_members[project.id]
            ],
            "timeline": timeline_rows,
            "filtros": {
                "projetos": [
                    {"label": project["nome"], "value": project["id"]}
                    for project in project_rows if project["cards"]
                ],
                "cards": [
                    {
                        "label": f"{next((project.nome for project in projects if project.id == column_project[card.column_id]), 'Projeto')} · {card.titulo}",
                        "value": card.id,
                    }
                    for card, _ in filtered
                ],
                "colaboradores": [
                    {"label": name, "value": employee_id}
                    for employee_id, name in sorted(employees.items(), key=lambda item: item[1])
                ],
                "status": sorted({column_status.get(card.column_id, "") for card, _ in filtered}),
            },
        })
    def _serialize_many(self, projects):
        """Serializa projetos em lote e evita consultas repetidas por card."""
        projects = list(projects)
        project_ids = [project.id for project in projects]
        if not project_ids:
            return []

        project_members = defaultdict(list)
        for project_id, employee_id, name in (
            db.session.query(ProjectMember.project_id, Users.id, Users.nome)
            .join(Users, Users.id == ProjectMember.employee_id)
            .filter(ProjectMember.project_id.in_(project_ids))
            .all()
        ):
            project_members[project_id].append({
                "id": employee_id,
                "nome": name,
                "iniciais": self._initials(name),
                "avatarColor": self._color(employee_id),
            })

        columns = (
            ProjectColumn.query.filter(ProjectColumn.project_id.in_(project_ids))
            .order_by(ProjectColumn.project_id.asc(), ProjectColumn.ordem.asc())
            .all()
        )
        columns_by_project = defaultdict(list)
        column_project_ids = {}
        for column in columns:
            columns_by_project[column.project_id].append(column)
            column_project_ids[column.id] = column.project_id

        cards = (
            ProjectCard.query.filter(ProjectCard.column_id.in_(column_project_ids or [0]))
            .order_by(ProjectCard.column_id.asc(), ProjectCard.ordem.asc())
            .all()
        )
        card_ids = [card.id for card in cards]
        card_members = defaultdict(list)
        for card_id, employee_id, name in (
            db.session.query(ProjectCardMember.card_id, Users.id, Users.nome)
            .join(Users, Users.id == ProjectCardMember.employee_id)
            .filter(ProjectCardMember.card_id.in_(card_ids or [0]))
            .all()
        ):
            card_members[card_id].append({
                "id": employee_id,
                "nome": name,
                "iniciais": self._initials(name),
                "avatarColor": self._color(employee_id),
            })

        comments_by_card = defaultdict(list)
        for comment, author in (
            db.session.query(ProjectCardComment, Users.nome)
            .outerjoin(Users, Users.id == ProjectCardComment.autor_id)
            .filter(ProjectCardComment.card_id.in_(card_ids or [0]))
            .order_by(ProjectCardComment.card_id.asc(), ProjectCardComment.created_at.asc(), ProjectCardComment.id.asc())
            .all()
        ):
            comments_by_card[comment.card_id].append({
                "id": comment.id,
                "autor_id": comment.autor_id,
                "autor": author or "Usuário removido",
                "conteudo": comment.conteudo,
                "created_at": comment.created_at.isoformat() if comment.created_at else None,
                "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
            })

        files_by_card = defaultdict(list)
        for file, uploader in (
            db.session.query(ProjectCardFile, Users.nome)
            .outerjoin(Users, Users.id == ProjectCardFile.enviado_por_usuario_id)
            .filter(ProjectCardFile.card_id.in_(card_ids or [0]))
            .order_by(ProjectCardFile.card_id.asc(), ProjectCardFile.created_at.desc())
            .all()
        ):
            files_by_card[file.card_id].append({
                "id": file.id,
                "nome_original": file.nome_original,
                "mime_type": file.mime_type,
                "tamanho_bytes": file.tamanho_bytes,
                "enviado_por_usuario_id": file.enviado_por_usuario_id,
                "enviado_por": uploader or "Usuário removido",
                "created_at": file.created_at.isoformat() if file.created_at else None,
                "url": f"/projetos/cards/{file.card_id}/arquivos/{file.id}",
            })

        card_ids_by_column = defaultdict(list)
        cards_by_column = defaultdict(list)
        cards_payload = defaultdict(dict)
        for card in cards:
            members = card_members[card.id]
            card_payload = {
                "id": card.id,
                "titulo": card.titulo,
                "descricao": card.descricao or "",
                "etiqueta": card.etiqueta,
                "data_inicio": card.data_inicio.isoformat() if card.data_inicio else None,
                "data_fim": card.data_fim.isoformat() if card.data_fim else None,
                "concluida_em": card.concluida_em.isoformat() if card.concluida_em else None,
                "created_at": card.created_at.isoformat() if card.created_at else None,
                "memberIds": [member["id"] for member in members],
                "members": members,
                "comentarios": comments_by_card[card.id],
                "arquivos": files_by_card[card.id],
            }
            project_id = column_project_ids[card.column_id]
            card_ids_by_column[card.column_id].append(card.id)
            cards_by_column[card.column_id].append(card_payload)
            cards_payload[project_id][card.id] = card_payload

        return [
            {
                "id": project.id,
                "nome": project.nome,
                "cor": project.cor,
                "donoId": project.dono,
                "memberIds": [member["id"] for member in project_members[project.id]],
                "members": project_members[project.id],
                "columns": [
                    {
                        "id": column.id,
                        "titulo": column.titulo,
                        "cardIds": card_ids_by_column[column.id],
                        "cards": cards_by_column[column.id],
                    }
                    for column in columns_by_project[project.id]
                ],
                "cards": cards_payload[project.id],
            }
            for project in projects
        ]

    def _serialize(self, project):
        return self._serialize_many([project])[0]

    def _initials(self, name):
        parts = (name or "").split()
        return "".join([part[0] for part in parts[:2]]).upper() or "U"

    def _color(self, seed):
        colors = ["#7c5cff", "#22a3a3", "#e0763a", "#c14b6b", "#3d78c9", "#2f9e44"]
        return colors[int(seed or 0) % len(colors)]

    @staticmethod
    def _project_for_card(card):
        return (
            Project.query.join(ProjectColumn, ProjectColumn.project_id == Project.id)
            .filter(ProjectColumn.id == card.column_id)
            .first()
        )

    @staticmethod
    def _can_access_project(project, user_id):
        return bool(
            project
            and (
                project.dono == user_id
                or ProjectMember.query.filter_by(
                    project_id=project.id,
                    employee_id=user_id,
                ).first()
            )
        )

    @staticmethod
    def _card_recipient_emails(card_id):
        return [
            row.email
            for row in (
                db.session.query(Users.email)
                .join(ProjectCardMember, ProjectCardMember.employee_id == Users.id)
                .filter(ProjectCardMember.card_id == card_id)
                .all()
            )
            if row.email
        ]

    def _notify_card(self, card, event, detail=""):
        notify_card_members(
            self._card_recipient_emails(card.id),
            f"TM Hub | Card {event}: {card.titulo}",
            f"O card '{card.titulo}' foi {event.lower()}.\n{detail}".strip(),
        )

    @staticmethod
    def _delete_card_files(card_id):
        for file in ProjectCardFile.query.filter_by(card_id=card_id).all():
            path = PROJECT_FILES_DIR / Path(file.caminho_arquivo).name
            if path.is_file():
                try:
                    path.unlink()
                except OSError:
                    current_app.logger.exception("Não foi possível remover arquivo do card %s", card_id)
            db.session.delete(file)

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
        if self._is_admin(user_id):
            query = Project.query
        else:
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
        response = self._serialize_many(projects)

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
        if "columns" in body and "cards" in body:
            card_ids = [
                card.id
                for card in ProjectCard.query.join(ProjectColumn)
                .filter(ProjectColumn.project_id == project.id)
                .all()
            ]
            for card in ProjectCard.query.filter(ProjectCard.id.in_(card_ids or [0])).all():
                self._notify_card(card, "atualizado")
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
        for card_id in card_ids:
            self._delete_card_files(card_id)
        ProjectCardComment.query.filter(ProjectCardComment.card_id.in_(card_ids or [0])).delete(synchronize_session=False)
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
                try:
                    data_inicio = _parse_datetime(card_payload.get("data_inicio"))
                    data_fim = _parse_datetime(card_payload.get("data_fim"))
                except ValueError:
                    data_inicio, data_fim = card.data_inicio, card.data_fim
                card.data_inicio = data_inicio or card.data_inicio or card.created_at or dt.now()
                card.data_fim = data_fim
                if "conclu" in str(column.titulo or "").casefold():
                    card.concluida_em = card.concluida_em or dt.now()
                else:
                    card.concluida_em = None
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
            self._delete_card_files(card.id)
            ProjectCardComment.query.filter_by(card_id=card.id).delete(synchronize_session=False)
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
        try:
            data_inicio = _parse_datetime(body.get("data_inicio")) or dt.now()
            data_fim = _parse_datetime(body.get("data_fim"))
        except ValueError as error:
            return jsonify(str(error)), 400
        if data_fim and data_fim < data_inicio:
            return jsonify("A data final não pode ser anterior à data inicial."), 400
        card = ProjectCard(
            column_id=column.id,
            titulo=title,
            descricao=body.get("descricao") or "",
            etiqueta=body.get("etiqueta"),
            ordem=order,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        db.session.add(card)
        db.session.flush()
        self._sync_card_members(card.id, [_as_int(item) for item in body.get("memberIds", [])])
        db.session.commit()
        self._notify_card(card, "criado")
        return jsonify(self._serialize(Project.query.filter_by(id=project_id).first())), 201

    @safe_route
    def update_card(self, card_id, token_data):
        card = ProjectCard.query.filter_by(id=card_id).first()
        if not card:
            return jsonify("Card nao encontrado"), 404

        project = self._project_for_card(card)
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
        try:
            data_inicio = _parse_datetime(body.get("data_inicio")) if "data_inicio" in body else card.data_inicio
            data_fim = _parse_datetime(body.get("data_fim")) if "data_fim" in body else card.data_fim
        except ValueError as error:
            return jsonify(str(error)), 400
        if not data_inicio:
            data_inicio = card.created_at or dt.now()
        if data_fim and data_fim < data_inicio:
            return jsonify("A data final não pode ser anterior à data inicial."), 400
        card.data_inicio = data_inicio
        card.data_fim = data_fim
        if "memberIds" in body:
            self._sync_card_members(card.id, [_as_int(item) for item in body["memberIds"]])

        db.session.commit()
        self._notify_card(card, "atualizado")
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
        self._delete_card_files(card.id)
        ProjectCardComment.query.filter_by(card_id=card.id).delete(synchronize_session=False)
        db.session.delete(card)
        db.session.commit()
        return jsonify(self._serialize(project)), 200

    @safe_route
    def create_comment(self, card_id, token_data):
        card = db.session.get(ProjectCard, card_id)
        project = self._project_for_card(card) if card else None
        user_id = _as_int(token_data.get("id"))
        if not self._can_access_project(project, user_id):
            return jsonify("Sem permissão para comentar neste card."), 403
        content = str((rq.get_json(silent=True) or {}).get("conteudo") or "").strip()
        if not content:
            return jsonify("Informe o comentário."), 400
        comment = ProjectCardComment(card_id=card.id, autor_id=user_id, conteudo=content)
        db.session.add(comment)
        db.session.commit()
        self._notify_card(card, "comentado", content)
        return jsonify(self._serialize(project)), 201

    @safe_route
    def update_comment(self, comment_id, token_data):
        comment = db.session.get(ProjectCardComment, comment_id)
        card = db.session.get(ProjectCard, comment.card_id) if comment else None
        project = self._project_for_card(card) if card else None
        user_id = _as_int(token_data.get("id"))
        if not comment:
            return jsonify("Comentário não encontrado."), 404
        if not self._can_access_project(project, user_id):
            return jsonify("Sem permissão para alterar este comentário."), 403
        if comment.autor_id != user_id and project.dono != user_id:
            return jsonify("Somente o autor ou dono do projeto pode alterar o comentário."), 403
        content = str((rq.get_json(silent=True) or {}).get("conteudo") or "").strip()
        if not content:
            return jsonify("Informe o comentário."), 400
        comment.conteudo = content
        db.session.commit()
        self._notify_card(card, "atualizado", "Um comentário foi alterado.")
        return jsonify(self._serialize(project))

    @safe_route
    def delete_comment(self, comment_id, token_data):
        comment = db.session.get(ProjectCardComment, comment_id)
        card = db.session.get(ProjectCard, comment.card_id) if comment else None
        project = self._project_for_card(card) if card else None
        user_id = _as_int(token_data.get("id"))
        if not comment:
            return jsonify("Comentário não encontrado."), 404
        if not self._can_access_project(project, user_id) or (
            comment.autor_id != user_id and project.dono != user_id
        ):
            return jsonify("Sem permissão para excluir este comentário."), 403
        db.session.delete(comment)
        db.session.commit()
        return jsonify(self._serialize(project))

    @safe_route
    def upload_card_file(self, card_id, token_data):
        card = db.session.get(ProjectCard, card_id)
        project = self._project_for_card(card) if card else None
        user_id = _as_int(token_data.get("id"))
        if not self._can_access_project(project, user_id):
            return jsonify("Sem permissão para anexar arquivos neste card."), 403
        uploaded = rq.files.get("arquivo")
        if not uploaded or not uploaded.filename:
            return jsonify("Selecione um arquivo."), 400
        original_name = secure_filename(uploaded.filename)
        extension = Path(original_name).suffix.lower()
        if not original_name or extension not in ALLOWED_PROJECT_FILE_EXTENSIONS:
            return jsonify("Formato de arquivo não permitido."), 400
        uploaded.stream.seek(0, 2)
        size = uploaded.stream.tell()
        uploaded.stream.seek(0)
        if size <= 0 or size > MAX_PROJECT_FILE_SIZE:
            return jsonify("O arquivo deve ter entre 1 byte e 15 MB."), 400
        PROJECT_FILES_DIR.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid4().hex}{extension}"
        uploaded.save(PROJECT_FILES_DIR / stored_name)
        db.session.add(ProjectCardFile(
            card_id=card.id,
            enviado_por_usuario_id=user_id,
            nome_original=original_name,
            caminho_arquivo=stored_name,
            mime_type=uploaded.mimetype,
            tamanho_bytes=size,
        ))
        db.session.commit()
        self._notify_card(card, "atualizado", f"Novo arquivo: {original_name}")
        return jsonify(self._serialize(project)), 201

    @safe_route
    def download_card_file(self, card_id, file_id, token_data):
        file = ProjectCardFile.query.filter_by(id=file_id, card_id=card_id).first()
        card = db.session.get(ProjectCard, card_id)
        project = self._project_for_card(card) if card else None
        if not file:
            return jsonify("Arquivo não encontrado."), 404
        if not self._can_access_project(project, _as_int(token_data.get("id"))):
            return jsonify("Sem permissão para baixar este arquivo."), 403
        return send_from_directory(
            PROJECT_FILES_DIR,
            file.caminho_arquivo,
            as_attachment=True,
            download_name=file.nome_original,
        )

    @safe_route
    def delete_card_file(self, card_id, file_id, token_data):
        file = ProjectCardFile.query.filter_by(id=file_id, card_id=card_id).first()
        card = db.session.get(ProjectCard, card_id)
        project = self._project_for_card(card) if card else None
        user_id = _as_int(token_data.get("id"))
        if not file:
            return jsonify("Arquivo não encontrado."), 404
        if not self._can_access_project(project, user_id) or (
            file.enviado_por_usuario_id != user_id and project.dono != user_id
        ):
            return jsonify("Sem permissão para excluir este arquivo."), 403
        path = PROJECT_FILES_DIR / file.caminho_arquivo
        db.session.delete(file)
        db.session.commit()
        try:
            path.unlink(missing_ok=True)
        except OSError:
            current_app.logger.exception("Não foi possível remover anexo do card")
        return jsonify(self._serialize(project))
