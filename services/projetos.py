from collections import defaultdict
from urllib import response
from models.pj_projects import Project
from models.pj_card import ProjectCard
from models.pj_card_member import ProjectCardMember
from models.pj_column import ProjectColumn
from models.pj_members import ProjectMember
from models.colaboradores import Employees
from utils.db import db
from flask import jsonify, request as rq

class ProjectService:
    def read(self):
        project_id = rq.args.get("id")
        
        projects = Project.query
        if project_id: projects.filter_by(id=id)
        projects = projects.all()
        response = []
        
        for project in projects:
            # ============================
            # Membros do projeto ==========
            # ============================
            members = (
                db.session.query(Employees.id, Employees.nome)
                .join(ProjectMember, ProjectMember.employee_id == Employees.id)
                .filter(ProjectMember.project_id == project.id)
                .all()
            )

            members = [{"id": item.id, "nome": item.nome} for item in members]

            # ============================
            # Colunas =====================
            # ============================
            columns = (
                ProjectColumn.query.filter_by(project_id=project.id)
                .order_by(ProjectColumn.ordem)
                .all()
            )

            # ============================
            # Cards ====================
            # ============================
            cards = (
                ProjectCard.query.filter(ProjectCard.column_id.in_([c.id for c in columns]))
                .order_by(ProjectCard.ordem)
                .all()
            )

            # ============================
            # Responsáveis dos cards
            # ============================
            card_members = (
                db.session.query(ProjectCardMember.card_id, Employees.id, Employees.nome)
                .join(Employees, Employees.id == ProjectCardMember.employee_id)
                .all()
            )

            members_by_card = defaultdict(list)

            for item in card_members:

                members_by_card[item.card_id].append({"id": item.id, "nome": item.nome})

            # ============================
            # Organiza cards por coluna
            # ============================
            cards_by_column = defaultdict(list)
            for card in cards:
                cards_by_column[card.column_id].append(
                    {
                        "id": card.id,
                        "titulo": card.titulo,
                        "descricao": card.descricao,
                        "etiqueta": card.etiqueta,
                        "memberIds": [member["id"] for member in members_by_card[card.id]],
                        "members": members_by_card[card.id],
                    }
                )

            # ============================
            # Retorno
            # ============================
            response.append(
                {
                    "id": project.id,
                    "nome": project.nome,
                    "cor": project.cor,
                    "members": members,
                    "columns": [
                        {
                            "id": column.id,
                            "titulo": column.titulo,
                            "cards": cards_by_column[column.id],
                        }
                        for column in columns
                    ],
                }
            ) 
        
        return jsonify(response)

