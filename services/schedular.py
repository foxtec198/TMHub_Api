from datetime import datetime as dt, timedelta
from os import getenv
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from flask import jsonify, request, send_from_directory
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from models.colaboradores import Employees
from models.schedular import SchedularAccess
from models.schedular_rotinas import (
    SchedularRoutine,
    SchedularRoutineCollaborator,
    SchedularRoutineStructure,
)
from models.schedular_checklists import SchedularChecklist, SchedularChecklistItem
from models.schedular_tarefas import (
    SchedularTask,
    SchedularTaskCollaborator,
    SchedularTaskEvidence,
    SchedularTaskGeolocation,
    SchedularTaskHistory,
    SchedularTaskResponse,
)
from models.centros_de_custo import CostCenters
from models.estrutura import StructureLocation
from utils.db import db
from utils.password_security import hash_password, is_strong_password
from utils.schedular_auth import (
    issue_schedular_token,
    schedular_route,
    tmhub_admin_session,
    verify_schedular_password,
)

SYSTEM_TZ = ZoneInfo("America/Sao_Paulo")
SCHEDULAR_EVIDENCE_DIR = Path(
    getenv("SCHEDULAR_EVIDENCE_DIR")
    or Path(__file__).resolve().parents[1] / "storage" / "schedular"
)
MAX_SCHEDULAR_EVIDENCE_SIZE = 10 * 1024 * 1024
IMAGE_EVIDENCE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
EVIDENCE_TYPES = {"camera", "image", "barcode", "qrcode", "signature"}
UNFINISHED_TASK_STATUSES = (
    "aberta",
    "pendente",
    "em_andamento",
    "pausada",
    "atrasada",
)


class SchedularService:
    @staticmethod
    def _configured_evidences(item):
        """Supports legacy strings and the {tipo, obrigatoria} configuration."""
        result = []
        for evidence in item.evidencias or []:
            if isinstance(evidence, str):
                result.append({"tipo": evidence, "obrigatoria": True})
            elif isinstance(evidence, dict) and evidence.get("tipo"):
                result.append(
                    {
                        "tipo": str(evidence["tipo"]),
                        "obrigatoria": bool(evidence.get("obrigatoria", True)),
                    }
                )
        return [entry for entry in result if entry["tipo"] in EVIDENCE_TYPES]

    @staticmethod
    def _evidence_payload(evidence):
        return {
            "id": evidence.id,
            "tipo": evidence.tipo,
            "valor": evidence.valor,
            "obrigatoria": evidence.obrigatoria,
            "coletada_em": evidence.coletada_em.isoformat() if evidence.coletada_em else None,
            "url": f"/schedular/evidencias/{evidence.id}/arquivo"
            if evidence.tipo in {"camera", "image", "signature"}
            else None,
        }

    @classmethod
    def _response_is_complete(cls, response, item):
        if not response:
            return False
        has_value = response.valor is not None and response.valor != "" and response.valor != {}
        evidences = SchedularTaskEvidence.query.filter_by(resposta_id=response.id).all()
        collected_types = {evidence.tipo for evidence in evidences}
        required = {
            evidence["tipo"]
            for evidence in cls._configured_evidences(item)
            if evidence["obrigatoria"]
        }
        return has_value and required.issubset(collected_types)

    @staticmethod
    def _parse_datetime(value):
        if not value:
            return None
        try:
            parsed = dt.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed.replace(tzinfo=SYSTEM_TZ) if parsed.tzinfo is None else parsed.astimezone(SYSTEM_TZ)
        except ValueError as error:
            raise ValueError("Informe uma data/hora vÃ¡lida.") from error

    @staticmethod
    def _now():
        return dt.now(SYSTEM_TZ)

    @staticmethod
    def _step(routine):
        recurrence = routine.recorrencia_tipo or routine.recorrencia
        if recurrence == "horas":
            return timedelta(hours=max(1, int(routine.intervalo_horas or 1)))
        if recurrence in {"dia", "diaria", "horario"}:
            return timedelta(days=max(1, int((routine.configuracao or {}).get("intervalo_dias", 1))))
        if recurrence == "semanal":
            return timedelta(days=7)
        if recurrence == "mensal":
            return timedelta(days=30)
        return None

    @classmethod
    def _next_from_anchor(cls, anchor, routine, now=None):
        """Keeps the date/time selected by the operator as the recurrence anchor."""
        now = now or cls._now()
        if not anchor:
            return now
        anchor = anchor.replace(tzinfo=SYSTEM_TZ) if anchor.tzinfo is None else anchor.astimezone(SYSTEM_TZ)
        if anchor >= now or (routine.recorrencia_tipo or routine.recorrencia) == "data":
            return anchor
        step = cls._step(routine)
        if not step:
            return anchor
        return anchor + step * (int((now - anchor).total_seconds() // step.total_seconds()) + 1)

    @staticmethod
    def _links_for(routine):
        links = SchedularRoutineStructure.query.filter_by(rotina_id=routine.id, ativo=True).all()
        if not links and routine.local_id:
            link = SchedularRoutineStructure(rotina_id=routine.id, estrutura_id=routine.local_id, origem="principal")
            db.session.add(link)
            db.session.flush()
            links = [link]
        return links

    @staticmethod
    def _checklist_payload(checklist):
        items = SchedularChecklistItem.query.filter_by(checklist_id=checklist.id).order_by(SchedularChecklistItem.ordem, SchedularChecklistItem.id).all()
        return {**checklist.to_dict(), "itens": [item.to_dict() for item in items]}

    @staticmethod
    def _routine_payload(routine):
        employee = db.session.get(Employees, routine.colaborador_responsavel_id) if routine.colaborador_responsavel_id else None
        collaborator_rows = SchedularRoutineCollaborator.query.filter_by(rotina_id=routine.id).all()
        collaborator_ids = [row.colaborador_id for row in collaborator_rows] or ([routine.colaborador_responsavel_id] if routine.colaborador_responsavel_id else [])
        collaborators = Employees.query.filter(Employees.id.in_(collaborator_ids)).order_by(Employees.nome).all() if collaborator_ids else []
        local = db.session.get(StructureLocation, routine.local_id)
        center = db.session.get(CostCenters, routine.centro_custo_id)
        checklist = db.session.get(SchedularChecklist, routine.checklist_id) if routine.checklist_id else None
        parent = db.session.get(SchedularRoutine, routine.rotina_pai_id) if routine.rotina_pai_id else None
        links = SchedularRoutineStructure.query.filter_by(rotina_id=routine.id).all()
        return {
            **routine.to_dict(),
            "colaborador": employee.nome if employee else None,
            "colaborador_matricula": employee.matricula if employee else None,
            "colaborador_ids": collaborator_ids,
            "colaboradores": [
                {"id": collaborator.id, "nome": collaborator.nome, "matricula": collaborator.matricula}
                for collaborator in collaborators
            ],
            "checklist": checklist.nome if checklist else None,
            "local": local.nome if local else None,
            "contrato": center.local if center else None,
            "estrutura": f"{center.local} / {local.nome}" if center and local else None,
            "rotina_pai_id": routine.rotina_pai_id,
            "rotina_pai": parent.nome if parent else None,
            "instancias_vinculadas": SchedularRoutine.query.filter_by(rotina_pai_id=routine.id).count(),
            "vinculos": [{"id": link.id, "estrutura_id": link.estrutura_id, "origem": link.origem, "ativo": link.ativo} for link in links],
        }

    @staticmethod
    def _copy_parent_settings(parent, child):
        """Copies only the operational routine setup, never the linked structure."""
        for field in (
            "nome",
            "descricao",
            "recorrencia",
            "recorrencia_tipo",
            "intervalo_horas",
            "estimativa_minutos",
            "executar_apenas_um",
            "inicio_recorrencia",
            "proxima_execucao",
            "colaborador_responsavel_id",
            "checklist_id",
            "ativa",
        ):
            setattr(child, field, getattr(parent, field))
        child.configuracao = dict(parent.configuracao or {})

    @classmethod
    def _sync_linked_instances(cls, parent):
        for child in SchedularRoutine.query.filter_by(rotina_pai_id=parent.id).all():
            cls._copy_parent_settings(parent, child)
            cls._sync_routine_collaborators(
                child.id,
                cls._routine_collaborator_ids(parent),
            )

    @staticmethod
    def _routine_collaborator_ids(routine):
        ids = [
            row.colaborador_id
            for row in SchedularRoutineCollaborator.query.filter_by(
                rotina_id=routine.id,
            ).all()
        ]
        return ids or ([routine.colaborador_responsavel_id] if routine.colaborador_responsavel_id else [])

    @staticmethod
    def _sync_routine_collaborators(routine_id, collaborator_ids):
        ids = sorted({int(item) for item in collaborator_ids if item})
        SchedularRoutineCollaborator.query.filter_by(rotina_id=routine_id).delete()
        for collaborator_id in ids:
            db.session.add(SchedularRoutineCollaborator(
                rotina_id=routine_id,
                colaborador_id=collaborator_id,
            ))

    @staticmethod
    def _sync_task_collaborators(task_id, collaborator_ids):
        ids = sorted({int(item) for item in collaborator_ids if item})
        SchedularTaskCollaborator.query.filter_by(tarefa_id=task_id).delete()
        for collaborator_id in ids:
            db.session.add(SchedularTaskCollaborator(
                tarefa_id=task_id,
                colaborador_id=collaborator_id,
            ))

    @staticmethod
    def _can_execute_task(task, collaborator_id):
        return SchedularTaskCollaborator.query.filter_by(
            tarefa_id=task.id,
            colaborador_id=collaborator_id,
        ).first() is not None or task.colaborador_id == collaborator_id

    @staticmethod
    def _add_task_history(task_id, collaborator_id, action):
        db.session.add(SchedularTaskHistory(
            tarefa_id=task_id,
            colaborador_id=collaborator_id,
            acao=action,
        ))

    @staticmethod
    def _add_task_geolocation(task_id, collaborator_id, location, event_type):
        """Stores only valid browser-provided coordinates for task auditing."""
        if not location:
            return False
        if not isinstance(location, dict):
            raise ValueError("Localização inválida.")
        try:
            latitude = float(location.get("latitude"))
            longitude = float(location.get("longitude"))
            accuracy = location.get("accuracy")
            accuracy = float(accuracy) if accuracy not in (None, "") else None
        except (TypeError, ValueError) as error:
            raise ValueError("Localização inválida.") from error
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("Coordenadas de localização inválidas.")
        if accuracy is not None and accuracy < 0:
            raise ValueError("Precisão de localização inválida.")
        db.session.add(SchedularTaskGeolocation(
            tarefa_id=task_id,
            colaborador_id=collaborator_id,
            tipo=event_type,
            latitude=latitude,
            longitude=longitude,
            precisao_metros=accuracy,
            capturada_em=SchedularService._now(),
        ))
        return True

    @staticmethod
    def _cancel_unfinished_tasks(query, now):
        return query.filter(
            SchedularTask.status.in_(UNFINISHED_TASK_STATUSES),
        ).update(
            {"status": "cancelada", "cancelada_em": now},
            synchronize_session=False,
        )

    @classmethod
    def _reprogram_unfinished_tasks(cls, routine):
        """Moves operational tasks to the routine's new schedule.

        The task itself is preserved so its checklist answers, evidences and
        executor history remain attached to the same record. Completed and
        cancelled work is intentionally excluded.
        """
        if not routine.ativa or not routine.proxima_execucao:
            return 0

        tasks = (
            SchedularTask.query
            .filter(
                SchedularTask.rotina_id == routine.id,
                SchedularTask.status.in_(UNFINISHED_TASK_STATUSES),
            )
            .with_for_update()
            .order_by(
                SchedularTask.rotina_estrutura_id,
                SchedularTask.ocorrencia_em,
                SchedularTask.id,
            )
            .all()
        )
        if not tasks:
            return 0

        step = cls._step(routine)
        tasks_by_link = {}
        for task in tasks:
            tasks_by_link.setdefault(task.rotina_estrutura_id, []).append(task)

        reprogrammed = 0
        estimate = int(routine.estimativa_minutos or 15)
        for link_id, linked_tasks in tasks_by_link.items():
            next_occurrence = routine.proxima_execucao
            for index, task in enumerate(linked_tasks):
                # A one-off routine has only one valid occurrence. In the
                # unlikely event of legacy duplicate open tasks, retain the
                # additional records rather than risking their history.
                if index and not step:
                    continue

                while (
                    SchedularTask.query
                    .filter(
                        SchedularTask.rotina_estrutura_id == link_id,
                        SchedularTask.ocorrencia_em == next_occurrence,
                        SchedularTask.id != task.id,
                    )
                    .first()
                ):
                    if not step:
                        break
                    next_occurrence += step

                if not step and SchedularTask.query.filter(
                    SchedularTask.rotina_estrutura_id == link_id,
                    SchedularTask.ocorrencia_em == next_occurrence,
                    SchedularTask.id != task.id,
                ).first():
                    continue

                changed = (
                    task.ocorrencia_em != next_occurrence
                    or task.agendada_para != next_occurrence
                    or task.prazo_em != next_occurrence + timedelta(minutes=estimate)
                    or task.estimativa_minutos != estimate
                )
                task.ocorrencia_em = next_occurrence
                task.agendada_para = next_occurrence
                task.prazo_em = next_occurrence + timedelta(minutes=estimate)
                task.estimativa_minutos = estimate
                if changed:
                    # The original task keeps every answer and evidence. The
                    # history records that its schedule was changed by the
                    # administrative routine configuration.
                    cls._add_task_history(task.id, None, "reprogramada")
                    reprogrammed += 1

                if step:
                    next_occurrence += step

        return reprogrammed

    @classmethod
    def _remove_routine_operationally(cls, routine, now):
        """Detach a routine without deleting completed task history."""
        cls._cancel_unfinished_tasks(
            SchedularTask.query.filter(SchedularTask.rotina_id == routine.id),
            now,
        )
        links = SchedularRoutineStructure.query.filter_by(
            rotina_id=routine.id,
        ).all()
        for link in links:
            cls._cancel_unfinished_tasks(
                SchedularTask.query.filter(
                    SchedularTask.rotina_estrutura_id == link.id,
                ),
                now,
            )
            link.ativo = False
            # Historical tasks retain the link id; clearing this FK releases
            # the location and avoids a removed instance blocking Structure.
            link.estrutura_id = None

        routine.ativa = False
        routine.proxima_execucao = None
        routine.rotina_pai_id = None
        routine.local_id = None
    def login(self):
        body = request.get_json(silent=True) or {}
        matricula = str(body.get("matricula") or "").strip()
        password = str(body.get("password") or "")
        if not matricula or not password:
            return jsonify("Informe a matrÃ­cula e a senha."), 400
        try:
            matricula_int = int(matricula)
        except ValueError:
            return jsonify("A matrÃ­cula deve conter apenas nÃºmeros."), 400

        employee = Employees.query.filter_by(matricula=matricula_int).first()
        if not employee:
            return jsonify("Colaborador nÃ£o encontrado."), 404
        access = SchedularAccess.query.filter_by(colaborador_id=employee.id).first()
        if not access or not access.ativo:
            return jsonify("Este colaborador ainda nÃ£o possui acesso ao Schedular."), 403
        valid, needs_rehash = verify_schedular_password(password, access.senha_hash)
        if not valid:
            return jsonify("Senha incorreta."), 400
        if needs_rehash:
            access.senha_hash = hash_password(password)
        access.ultimo_login = dt.now()
        db.session.commit()
        return jsonify({
            "access_token": issue_schedular_token(access),
            "colaborador": {
                "id": employee.id,
                "matricula": employee.matricula,
                "nome": employee.nome,
                "centro_id": employee.centro_id,
            },
            "perfil": access.perfil,
            "senha_pendente": bool(access.senha_pendente),
        }), 200

    @schedular_route
    def session(self, schedular_session):
        employee = schedular_session["employee"]
        access = schedular_session["access"]
        return jsonify({
            "colaborador": {
                "id": employee.id,
                "matricula": employee.matricula,
                "nome": employee.nome,
                "centro_id": employee.centro_id,
            },
            "perfil": access.perfil,
            "senha_pendente": bool(access.senha_pendente),
        })

    def provision_access(self):
        _, error = tmhub_admin_session()
        if error:
            return error
        body = request.get_json(silent=True) or {}
        try:
            employee_id = int(body.get("colaborador_id"))
        except (TypeError, ValueError):
            return jsonify("Informe um colaborador vÃ¡lido."), 400
        employee = db.session.get(Employees, employee_id)
        if not employee:
            return jsonify("Colaborador nÃ£o encontrado."), 404
        password = str(body.get("senha") or "").strip()
        if not is_strong_password(password):
            return jsonify("A senha deve ter ao menos 8 caracteres, maiÃºscula, minÃºscula, nÃºmero e sÃ­mbolo."), 400
        access = SchedularAccess.query.filter_by(colaborador_id=employee.id).first()
        if not access:
            access = SchedularAccess(colaborador_id=employee.id, senha_hash=hash_password(password))
            db.session.add(access)
        else:
            access.senha_hash = hash_password(password)
            access.ativo = True
            access.senha_pendente = True
            access.token_version = int(access.token_version or 0) + 1
        db.session.commit()
        return jsonify({
            "message": "Acesso do Schedular criado/atualizado com sucesso.",
            "colaborador_id": employee.id,
            "matricula": employee.matricula,
        }), 201

    def read_accesses(self):
        _, error = tmhub_admin_session()
        if error:
            return error
        employees = {employee.id: employee for employee in Employees.query.order_by(Employees.nome).all()}
        accesses = SchedularAccess.query.order_by(SchedularAccess.created_at.desc()).all()
        return jsonify([{
            "id": access.id,
            "colaborador_id": access.colaborador_id,
            "matricula": employees.get(access.colaborador_id).matricula if employees.get(access.colaborador_id) else None,
            "colaborador": employees.get(access.colaborador_id).nome if employees.get(access.colaborador_id) else "Colaborador removido",
            "perfil": access.perfil,
            "ativo": access.ativo,
            "ultimo_login": access.ultimo_login,
        } for access in accesses])

    def create_routine(self):
        user, error = tmhub_admin_session()
        if error:
            return error
        body = request.get_json(silent=True) or {}
        try:
            center_id = int(body.get("centro_custo_id"))
            local_id = int(body.get("local_id"))
        except (TypeError, ValueError):
            return jsonify("Informe um contrato e um local vÃ¡lidos."), 400
        center = db.session.get(CostCenters, center_id)
        local = db.session.get(StructureLocation, local_id)
        if not center:
            return jsonify("Contrato nÃ£o encontrado."), 404
        if not local or local.centro_custo_id != center.id:
            return jsonify("O local nÃ£o pertence ao contrato informado."), 400
        requested_collaborators = body.get("colaborador_ids")
        if not isinstance(requested_collaborators, list):
            requested_collaborators = [body.get("colaborador_responsavel_id")]
        try:
            collaborator_ids = sorted({int(item) for item in requested_collaborators if item not in (None, "")})
        except (TypeError, ValueError):
            return jsonify("Informe colaboradores válidos."), 400
        if not collaborator_ids:
            return jsonify("Selecione o colaborador responsÃ¡vel."), 400
        collaborators = Employees.query.filter(Employees.id.in_(collaborator_ids), Employees.situacao == 1).all()
        if len(collaborators) != len(collaborator_ids):
            return jsonify("Colaborador responsÃ¡vel nÃ£o encontrado ou inativo."), 400
        checklist_id = body.get("checklist_id") or None
        checklist = db.session.get(SchedularChecklist, int(checklist_id)) if checklist_id else None
        if checklist_id and not checklist:
            return jsonify("Checklist nÃ£o encontrado."), 404
        nome = str(body.get("nome") or "").strip()
        if not nome:
            return jsonify("Informe o nome da rotina."), 400
        recorrencia = str(body.get("recorrencia_tipo") or body.get("recorrencia") or "semanal").strip().lower()
        if recorrencia not in {"data", "dia", "horario", "horas", "diaria", "semanal", "mensal"}:
            return jsonify("RecorrÃªncia invÃ¡lida."), 400
        interval = body.get("intervalo_horas")
        if recorrencia == "horas":
            try:
                interval = int(interval)
            except (TypeError, ValueError):
                return jsonify("Informe o intervalo em horas."), 400
            if interval <= 0:
                return jsonify("O intervalo de horas deve ser maior que zero."), 400
        try:
            estimated_minutes = int(body.get("estimativa_minutos") or 15)
        except (TypeError, ValueError):
            return jsonify("Estimativa inválida."), 400
        if estimated_minutes <= 0:
            return jsonify("A estimativa deve ser maior que zero.") , 400
        next_run = self._parse_datetime(body.get("proxima_execucao"))
        if not next_run:
            return jsonify("Informe a prÃ³xima execuÃ§Ã£o."), 400
        routine = SchedularRoutine(
            centro_custo_id=center.id,
            local_id=local.id,
            nome=nome,
            descricao=str(body.get("descricao") or "").strip() or None,
            recorrencia=recorrencia,
            recorrencia_tipo=recorrencia,
            intervalo_horas=interval,
            estimativa_minutos=estimated_minutes,
            inicio_recorrencia=next_run,
            # If the configured start is in the past, the first pending run is
            # calculated from that same anchor, never from the save timestamp.
            proxima_execucao=self._next_from_anchor(next_run, type("Schedule", (), {"recorrencia_tipo": recorrencia, "recorrencia": recorrencia, "intervalo_horas": interval, "configuracao": body.get("configuracao") if isinstance(body.get("configuracao"), dict) else {}})()),
            colaborador_responsavel_id=collaborator_ids[0],
            checklist_id=checklist.id if checklist else None,
            configuracao=body.get("configuracao") if isinstance(body.get("configuracao"), dict) else {},
            executar_apenas_um=bool(body.get("executar_apenas_um")),
            criado_por_usuario_id=user.id,
        )
        db.session.add(routine)
        db.session.flush()
        self._sync_routine_collaborators(routine.id, collaborator_ids)
        db.session.add(SchedularRoutineStructure(rotina_id=routine.id, estrutura_id=local.id, origem="principal"))
        db.session.commit()
        return jsonify({
            "message": "Rotina criada com sucesso.",
            "rotina": self._routine_payload(routine),
        }), 201

    def read_routines(self):
        _, error = tmhub_admin_session()
        if error:
            return error
        rows = (
            SchedularRoutine.query
            .filter(SchedularRoutine.local_id.isnot(None))
            .order_by(SchedularRoutine.created_at.desc())
            .all()
        )
        return jsonify([self._routine_payload(row) for row in rows])

    def update_routine(self, routine_id):
        user, error = tmhub_admin_session()
        if error:
            return error
        routine = (
            SchedularRoutine.query
            .filter_by(id=routine_id)
            .with_for_update()
            .first()
        )
        if not routine:
            return jsonify("Rotina nÃ£o encontrada."), 404
        body = request.get_json(silent=True) or {}
        if routine.rotina_pai_id and not body.get("desvincular_do_pai"):
            parent = db.session.get(SchedularRoutine, routine.rotina_pai_id)
            return jsonify(
                {
                    "code": "ROTINA_VINCULADA",
                    "message": "Esta é uma instância vinculada à rotina-pai. Ao alterar, ela será desvinculada e seguirá de forma independente.",
                    "rotina_pai_id": routine.rotina_pai_id,
                    "rotina_pai": parent.nome if parent else None,
                }
            ), 409
        if routine.rotina_pai_id and body.get("desvincular_do_pai"):
            routine.rotina_pai_id = None
        if "nome" in body and not str(body.get("nome") or "").strip():
            return jsonify("Informe o nome da rotina."), 400
        if "colaborador_ids" in body or "colaborador_responsavel_id" in body:
            requested_collaborators = body.get("colaborador_ids")
            if not isinstance(requested_collaborators, list):
                requested_collaborators = [body.get("colaborador_responsavel_id")]
            try:
                collaborator_ids = sorted({int(item) for item in requested_collaborators if item not in (None, "")})
            except (TypeError, ValueError):
                return jsonify("Informe colaboradores válidos."), 400
            collaborators = Employees.query.filter(Employees.id.in_(collaborator_ids), Employees.situacao == 1).all() if collaborator_ids else []
            if not collaborator_ids or len(collaborators) != len(collaborator_ids):
                return jsonify("Colaborador responsÃ¡vel nÃ£o encontrado ou inativo."), 400
            routine.colaborador_responsavel_id = collaborator_ids[0]
            self._sync_routine_collaborators(routine.id, collaborator_ids)
        if "checklist_id" in body:
            checklist = db.session.get(SchedularChecklist, body.get("checklist_id")) if body.get("checklist_id") else None
            if body.get("checklist_id") and not checklist:
                return jsonify("Checklist nÃ£o encontrado."), 404
            routine.checklist_id = checklist.id if checklist else None
        recurrence_changed = any(key in body for key in ("recorrencia", "recorrencia_tipo", "intervalo_horas", "configuracao", "proxima_execucao"))
        schedule_changed = recurrence_changed or "estimativa_minutos" in body
        if "proxima_execucao" in body:
            anchor = self._parse_datetime(body.get("proxima_execucao"))
            if not anchor:
                return jsonify("Informe a data e horÃ¡rio de recorrÃªncia."), 400
            routine.inicio_recorrencia = anchor
        if "intervalo_horas" in body:
            try:
                routine.intervalo_horas = int(body.get("intervalo_horas"))
            except (TypeError, ValueError):
                return jsonify("Intervalo de horas invÃ¡lido."), 400
            if routine.intervalo_horas <= 0:
                return jsonify("O intervalo de horas deve ser maior que zero."), 400
        if "estimativa_minutos" in body:
            try:
                routine.estimativa_minutos = int(body.get("estimativa_minutos"))
            except (TypeError, ValueError):
                return jsonify("Estimativa inválida."), 400
            if routine.estimativa_minutos <= 0:
                return jsonify("A estimativa deve ser maior que zero."), 400
        if "configuracao" in body and isinstance(body.get("configuracao"), dict):
            routine.configuracao = body["configuracao"]
        for field in ("nome", "descricao", "recorrencia", "recorrencia_tipo"):
            if field in body:
                setattr(routine, field, str(body.get(field) or "").strip() or None)
        if recurrence_changed:
            anchor = routine.inicio_recorrencia or routine.proxima_execucao
            routine.proxima_execucao = self._next_from_anchor(anchor, routine)
        if "ativa" in body:
            routine.ativa = bool(body.get("ativa"))
        if "executar_apenas_um" in body:
            routine.executar_apenas_um = bool(body.get("executar_apenas_um"))
        routines_to_reprogram = [routine]
        if not routine.rotina_pai_id:
            self._sync_linked_instances(routine)
            routines_to_reprogram.extend(
                SchedularRoutine.query.filter_by(rotina_pai_id=routine.id).all(),
            )
        if schedule_changed:
            for scheduled_routine in routines_to_reprogram:
                self._reprogram_unfinished_tasks(scheduled_routine)
        db.session.commit()
        return jsonify({"message": "Rotina atualizada com sucesso.", "rotina": self._routine_payload(routine)})

    def delete_routine(self, routine_id):
        _, error = tmhub_admin_session()
        if error:
            return error
        routine = db.session.get(SchedularRoutine, routine_id)
        if not routine:
            return jsonify("Rotina nÃ£o encontrada."), 404
        now = self._now()
        # Deleting a parent also retires every linked instance. Completed tasks
        # are never deleted: only unfinished work is cancelled.
        routines = [routine]
        if not routine.rotina_pai_id:
            routines.extend(
                SchedularRoutine.query.filter_by(rotina_pai_id=routine.id).all(),
            )
        for current in routines:
            self._remove_routine_operationally(current, now)
        db.session.commit()
        return jsonify("Rotina excluÃ­da com sucesso.")

    def routine_links(self, routine_id):
        user, error = tmhub_admin_session()
        if error:
            return error
        routine = db.session.get(SchedularRoutine, routine_id)
        if not routine:
            return jsonify("Rotina não encontrada."), 404
        if request.method == "GET":
            rows = SchedularRoutineStructure.query.filter_by(rotina_id=routine.id).all()
            root_id = routine.rotina_pai_id or routine.id
            instances = SchedularRoutine.query.filter_by(rotina_pai_id=root_id).all()
            return jsonify({
                "vinculos": [{**link.to_dict(), "local": (db.session.get(StructureLocation, link.estrutura_id).nome if db.session.get(StructureLocation, link.estrutura_id) else None)} for link in rows],
                "instancias": [self._routine_payload(instance) for instance in instances],
            })
        body = request.get_json(silent=True) or {}
        # Accept both spellings during the frontend transition. This branch
        # intentionally permits targets from any cost center in the user's branch.
        requested_instances = body.get("instancias") or body.get("instances")
        if isinstance(requested_instances, list):
            parent = db.session.get(SchedularRoutine, routine.rotina_pai_id) if routine.rotina_pai_id else routine
            created = []
            for target in requested_instances:
                try:
                    center_id = int(target.get("centro_custo_id"))
                    local_id = int(target.get("local_id"))
                except (AttributeError, TypeError, ValueError):
                    return jsonify("Informe contrato e local válidos em cada vínculo."), 400
                center = db.session.get(CostCenters, center_id)
                local = db.session.get(StructureLocation, local_id)
                if not center or not local or local.centro_custo_id != center.id:
                    return jsonify("Um dos locais informados não pertence ao contrato selecionado."), 400
                if center.id == parent.centro_custo_id and local.id == parent.local_id:
                    continue
                instance = SchedularRoutine.query.filter_by(
                    rotina_pai_id=parent.id,
                    centro_custo_id=center.id,
                    local_id=local.id,
                ).first()
                if instance:
                    continue
                instance = SchedularRoutine(
                    rotina_pai_id=parent.id,
                    centro_custo_id=center.id,
                    local_id=local.id,
                    criado_por_usuario_id=user.id,
                )
                self._copy_parent_settings(parent, instance)
                db.session.add(instance)
                db.session.flush()
                self._sync_routine_collaborators(
                    instance.id,
                    self._routine_collaborator_ids(parent),
                )
                db.session.add(
                    SchedularRoutineStructure(
                        rotina_id=instance.id,
                        estrutura_id=local.id,
                        origem="rotina_vinculada",
                    )
                )
                created.append(self._routine_payload(instance))
            db.session.commit()
            return jsonify(
                {
                    "message": f"{len(created)} instância(s) vinculada(s) à rotina-pai.",
                    "instancias": created,
                }
            ), 201
        try:
            structure_id = int(body.get("estrutura_id"))
        except (TypeError, ValueError):
            return jsonify("Informe a estrutura para vincular."), 400
        local = db.session.get(StructureLocation, structure_id)
        if not local:
            return jsonify("Estrutura não encontrada."), 404
        if local.centro_custo_id != routine.centro_custo_id:
            return jsonify("A estrutura precisa pertencer ao mesmo contrato da rotina."), 400
        link = SchedularRoutineStructure.query.filter_by(rotina_id=routine.id, estrutura_id=local.id).first()
        if link:
            link.ativo = True
        else:
            link = SchedularRoutineStructure(rotina_id=routine.id, estrutura_id=local.id, origem=str(body.get("origem") or "vinculo"))
            db.session.add(link)
        db.session.commit()
        return jsonify({"message": "Rotina vinculada à estrutura.", "vinculo": link.to_dict()}), 201

    def remove_routine_link(self, routine_id, link_id):
        _, error = tmhub_admin_session()
        if error:
            return error
        routine = db.session.get(SchedularRoutine, routine_id)
        if not routine:
            return jsonify("Rotina não encontrada."), 404
        link = SchedularRoutineStructure.query.filter_by(id=link_id, rotina_id=routine_id).first()
        if not link:
            return jsonify("Vínculo não encontrado."), 404
        now = self._now()
        if routine.local_id == link.estrutura_id:
            self._remove_routine_operationally(routine, now)
            db.session.commit()
            return jsonify("Rotina removida e tarefas em aberto canceladas; histórico preservado.")
        self._cancel_unfinished_tasks(
            SchedularTask.query.filter(SchedularTask.rotina_estrutura_id == link.id),
            now,
        )
        link.ativo = False
        link.estrutura_id = None
        db.session.commit()
        return jsonify("Vínculo removido; histórico preservado.")

    @staticmethod
    def _process_due_routines():
        now = SchedularService._now()
        processed = 0
        for routine in SchedularRoutine.query.filter(SchedularRoutine.ativa.is_(True), SchedularRoutine.proxima_execucao <= now).with_for_update().all():
            if not routine.colaborador_responsavel_id:
                continue
            occurrence = routine.proxima_execucao
            for link in SchedularService._links_for(routine):
                local = db.session.get(StructureLocation, link.estrutura_id)
                if not local:
                    continue
                exists = SchedularTask.query.filter_by(rotina_estrutura_id=link.id, ocorrencia_em=occurrence).first()
                if not exists:
                    task = SchedularTask(
                        rotina_id=routine.id,
                        rotina_estrutura_id=link.id,
                        origem="rotina",
                        colaborador_id=routine.colaborador_responsavel_id,
                        checklist_id=routine.checklist_id,
                        centro_custo_id=local.centro_custo_id,
                        local_id=local.id,
                        agendada_para=occurrence,
                        prazo_em=occurrence + timedelta(minutes=int(routine.estimativa_minutos or 15)),
                        estimativa_minutos=int(routine.estimativa_minutos or 15),
                        executar_apenas_um=bool(routine.executar_apenas_um),
                        ocorrencia_em=occurrence,
                    )
                    db.session.add(task)
                    db.session.flush()
                    SchedularService._sync_task_collaborators(
                        task.id,
                        SchedularService._routine_collaborator_ids(routine),
                    )
                    processed += 1
            if (routine.recorrencia_tipo or routine.recorrencia) == "data":
                routine.ativa = False
                routine.proxima_execucao = None
            else:
                # Move from the scheduled occurrence, preserving the anchor clock.
                routine.proxima_execucao = occurrence + SchedularService._step(routine)
        db.session.commit()
        return processed

    def process_routines(self):
        _, error = tmhub_admin_session()
        if error:
            return error
        return jsonify({"processadas": self._process_due_routines()})

    @staticmethod
    def _task_payload(task):
        routine = db.session.get(SchedularRoutine, task.rotina_id)
        employee = db.session.get(Employees, task.colaborador_id)
        executor = db.session.get(Employees, task.executor_colaborador_id) if task.executor_colaborador_id else None
        collaborator_rows = SchedularTaskCollaborator.query.filter_by(tarefa_id=task.id).all()
        collaborator_ids = [row.colaborador_id for row in collaborator_rows] or [task.colaborador_id]
        collaborators = Employees.query.filter(Employees.id.in_(collaborator_ids)).order_by(Employees.nome).all() if collaborator_ids else []
        local = db.session.get(StructureLocation, task.local_id)
        checklist = db.session.get(SchedularChecklist, task.checklist_id) if task.checklist_id else None
        items = SchedularChecklistItem.query.filter_by(checklist_id=task.checklist_id).order_by(SchedularChecklistItem.ordem).all() if task.checklist_id else []
        response_rows = SchedularTaskResponse.query.filter_by(tarefa_id=task.id).all()
        response_map = {response.checklist_item_id: response for response in response_rows}
        employee_ids = [row.respondido_por_colaborador_id for row in response_rows if row.respondido_por_colaborador_id]
        employee_names = {
            row.id: row.nome
            for row in Employees.query.filter(Employees.id.in_(employee_ids)).all()
        } if employee_ids else {}
        evidence_rows = SchedularTaskEvidence.query.filter(
            SchedularTaskEvidence.resposta_id.in_([response.id for response in response_rows] or [-1])
        ).order_by(SchedularTaskEvidence.coletada_em).all()
        evidence_by_response = {}
        for evidence in evidence_rows:
            evidence_by_response.setdefault(evidence.resposta_id, []).append(
                SchedularService._evidence_payload(evidence)
            )
        history_rows = SchedularTaskHistory.query.filter_by(tarefa_id=task.id).order_by(
            SchedularTaskHistory.created_at.asc(),
            SchedularTaskHistory.id.asc(),
        ).all()
        geolocation_rows = SchedularTaskGeolocation.query.filter_by(
            tarefa_id=task.id,
        ).order_by(
            SchedularTaskGeolocation.capturada_em.asc(),
            SchedularTaskGeolocation.id.asc(),
        ).all()
        history_employee_ids = [row.colaborador_id for row in history_rows if row.colaborador_id]
        history_employees = {
            row.id: row.nome
            for row in Employees.query.filter(Employees.id.in_(history_employee_ids or [-1])).all()
        }

        def response_payload(item):
            response = response_map.get(item.id)
            if not response:
                return None
            return {
                "valor": response.valor,
                "respondido_em": response.respondido_em.isoformat() if response.respondido_em else None,
                "respondido_por": employee_names.get(response.respondido_por_colaborador_id),
                "evidencias": evidence_by_response.get(response.id, []),
            }

        deadline = task.prazo_em or (
            task.agendada_para
            + timedelta(minutes=int(task.estimativa_minutos or 15))
            if task.agendada_para
            else None
        )
        is_late = bool(
            deadline
            and deadline < SchedularService._now()
            and task.status in {"aberta", "em_andamento", "pausada"}
        )
        return {**task.to_dict(), "origem": task.origem or "rotina", "tarefa": routine.nome if routine else "Rotina removida", "rotina": routine.nome if routine else None,
                "colaborador": employee.nome if employee else None,
                "colaborador_ids": collaborator_ids,
                "colaboradores": [{"id": row.id, "nome": row.nome, "matricula": row.matricula} for row in collaborators],
                "executor": executor.nome if executor else None,
                "historico": [
                    {"acao": row.acao, "colaborador_id": row.colaborador_id,
                     "colaborador": (
                         history_employees.get(row.colaborador_id, "Colaborador removido")
                         if row.colaborador_id
                         else "Sistema"
                     ),
                     "created_at": row.created_at.isoformat() if row.created_at else None}
                    for row in history_rows
                ],
                "geolocalizacoes": [
                    {
                        "id": row.id,
                        "tipo": row.tipo,
                        "colaborador_id": row.colaborador_id,
                        "latitude": row.latitude,
                        "longitude": row.longitude,
                        "precisao_metros": row.precisao_metros,
                        "capturada_em": row.capturada_em.isoformat()
                        if row.capturada_em
                        else None,
                    }
                    for row in geolocation_rows
                ],
                "local": local.nome if local else None,
                "checklist": checklist.nome if checklist else None, "itens": [{**item.to_dict(), "resposta": response_payload(item), "evidencias_configuradas": SchedularService._configured_evidences(item)} for item in items], "atrasada": is_late}

    def read_tasks(self):
        _, error = tmhub_admin_session()
        if error:
            return error
        query = SchedularTask.query
        status = request.args.get("status")
        if status:
            query = query.filter_by(status=status)
        return jsonify([self._task_payload(task) for task in query.order_by(SchedularTask.agendada_para.desc()).all()])

    @schedular_route
    def read_my_tasks(self, schedular_session):
        employee = schedular_session["employee"]
        rows = SchedularTask.query.outerjoin(
            SchedularTaskCollaborator,
            SchedularTaskCollaborator.tarefa_id == SchedularTask.id,
        ).filter(
            or_(
                SchedularTask.colaborador_id == employee.id,
                SchedularTaskCollaborator.colaborador_id == employee.id,
            ),
            SchedularTask.status.in_(("aberta", "em_andamento", "pausada")),
        ).distinct().order_by(SchedularTask.agendada_para.asc()).all()
        return jsonify([self._task_payload(task) for task in rows])

    @schedular_route
    def action_task(self, task_id, schedular_session):
        employee = schedular_session["employee"]
        task = SchedularTask.query.filter_by(id=task_id).with_for_update().first()
        if not task or not self._can_execute_task(task, employee.id):
            return jsonify("Tarefa não encontrada para este executor."), 404
        body = request.get_json(silent=True) or {}
        action = str(body.get("acao") or "").lower()
        now = self._now()
        transitions = {
            "iniciar": ("aberta", "em_andamento"),
            "pausar": ("em_andamento", "pausada"),
            "continuar": ("pausada", "em_andamento"),
            "finalizar": ("em_andamento", "concluida"),
        }
        if action == "finalizar":
            checklist_items = SchedularChecklistItem.query.filter_by(
                checklist_id=task.checklist_id
            ).all() if task.checklist_id else []
            mandatory = [
                item
                for item in checklist_items
                if item.obrigatorio
                or any(
                    evidence["obrigatoria"]
                    for evidence in self._configured_evidences(item)
                )
            ]
            responses = {
                row.checklist_item_id: row
                for row in SchedularTaskResponse.query.filter_by(tarefa_id=task.id).all()
            }
            if any(not self._response_is_complete(responses.get(item.id), item) for item in mandatory):
                return jsonify("Responda todos os itens obrigatórios antes de finalizar."), 409
        if action not in transitions or task.status != transitions[action][0]:
            return jsonify("Ação não permitida para o status atual da tarefa."), 409
        if task.executar_apenas_um:
            if task.executor_colaborador_id and task.executor_colaborador_id != employee.id:
                return jsonify("Esta tarefa já está sendo executada por outro colaborador."), 409
            if action == "iniciar" and not task.executor_colaborador_id:
                task.executor_colaborador_id = employee.id
        task.status = transitions[action][1]
        if action == "iniciar": task.iniciada_em = now
        if action == "pausar": task.pausada_em = now
        if action == "finalizar": task.concluida_em = now
        location_event = {
            "iniciar": "inicio",
            "finalizar": "finalizacao",
        }.get(action)
        if location_event:
            try:
                self._add_task_geolocation(
                    task.id,
                    employee.id,
                    body.get("geolocalizacao"),
                    location_event,
                )
            except ValueError as error:
                return jsonify(str(error)), 400
        self._add_task_history(task.id, employee.id, action)
        db.session.commit()
        return jsonify({"message": "Tarefa atualizada.", "tarefa": self._task_payload(task)})

    @schedular_route
    def save_task_geolocation(self, task_id, schedular_session):
        employee = schedular_session["employee"]
        task = SchedularTask.query.filter_by(id=task_id).with_for_update().first()
        if not task or not self._can_execute_task(task, employee.id):
            return jsonify("Tarefa não encontrada para este executor."), 404
        if task.executar_apenas_um and task.executor_colaborador_id != employee.id:
            return jsonify("Esta tarefa está bloqueada para o executor responsável."), 409
        if task.status != "em_andamento":
            return jsonify("A localização só pode ser registrada durante a execução."), 409
        try:
            self._add_task_geolocation(
                task.id,
                employee.id,
                (request.get_json(silent=True) or {}).get("geolocalizacao"),
                "execucao",
            )
        except ValueError as error:
            return jsonify(str(error)), 400
        db.session.commit()
        return jsonify({"message": "Localização registrada."}), 201

    @schedular_route
    def save_task_answers(self, task_id, schedular_session):
        task = db.session.get(SchedularTask, task_id)
        employee = schedular_session["employee"]
        if not task or not self._can_execute_task(task, employee.id):
            return jsonify("Tarefa não encontrada para este executor."), 404
        if task.executar_apenas_um and task.executor_colaborador_id and task.executor_colaborador_id != employee.id:
            return jsonify("Esta tarefa está bloqueada para o executor responsável."), 409
        if task.status not in {"em_andamento", "pausada"}:
            return jsonify("Inicie a tarefa antes de responder o checklist."), 409
        body = request.get_json(silent=True) or {}
        for answer in body.get("respostas") or []:
            item = db.session.get(SchedularChecklistItem, answer.get("checklist_item_id"))
            if not item or item.checklist_id != task.checklist_id:
                return jsonify("Item do checklist inválido."), 400
            response = SchedularTaskResponse.query.filter_by(tarefa_id=task.id, checklist_item_id=item.id).first()
            if not response:
                response = SchedularTaskResponse(tarefa_id=task.id, checklist_item_id=item.id)
                db.session.add(response)
            response.valor = answer.get("valor") if answer.get("valor") is not None else {}
            response.respondido_por_colaborador_id = employee.id
            response.respondido_em = self._now()
        db.session.commit()
        return jsonify({"message": "Respostas salvas.", "tarefa": self._task_payload(task)})

    @schedular_route
    def save_task_evidence(self, task_id, item_id, schedular_session):
        task = db.session.get(SchedularTask, task_id)
        employee = schedular_session["employee"]
        if not task or not self._can_execute_task(task, employee.id):
            return jsonify("Tarefa não encontrada para este executor."), 404
        if task.executar_apenas_um and task.executor_colaborador_id and task.executor_colaborador_id != employee.id:
            return jsonify("Esta tarefa está bloqueada para o executor responsável."), 409
        if task.status not in {"em_andamento", "pausada"}:
            return jsonify("Inicie a tarefa antes de registrar evidências."), 409
        item = db.session.get(SchedularChecklistItem, item_id)
        if not item or item.checklist_id != task.checklist_id:
            return jsonify("Item do checklist inválido."), 400

        evidence_type = str(request.form.get("tipo") or "").lower()
        allowed_types = {entry["tipo"] for entry in self._configured_evidences(item)}
        if evidence_type not in allowed_types:
            return jsonify("Este tipo de evidência não está configurado para a pergunta."), 400

        response = SchedularTaskResponse.query.filter_by(
            tarefa_id=task.id,
            checklist_item_id=item.id,
        ).first()
        if not response:
            response = SchedularTaskResponse(
                tarefa_id=task.id,
                checklist_item_id=item.id,
                valor={},
                respondido_por_colaborador_id=employee.id,
                respondido_em=self._now(),
            )
            db.session.add(response)
            db.session.flush()

        stored_value = str(request.form.get("valor") or "").strip()
        uploaded = request.files.get("arquivo")
        file_types = {"camera", "image", "signature"}
        if evidence_type in file_types:
            if not uploaded or not uploaded.filename:
                return jsonify("Envie a imagem ou assinatura coletada."), 400
            extension = Path(secure_filename(uploaded.filename)).suffix.lower()
            if extension not in IMAGE_EVIDENCE_EXTENSIONS:
                return jsonify("Formato inválido. Envie PNG, JPG, JPEG ou WEBP."), 400
            uploaded.stream.seek(0, 2)
            size = uploaded.stream.tell()
            uploaded.stream.seek(0)
            if size > MAX_SCHEDULAR_EVIDENCE_SIZE:
                return jsonify("A evidência deve ter no máximo 10 MB."), 400
            SCHEDULAR_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
            stored_name = f"{uuid4().hex}{extension}"
            uploaded.save(SCHEDULAR_EVIDENCE_DIR / stored_name)
            stored_value = stored_name
        elif evidence_type in {"barcode", "qrcode"}:
            if not stored_value:
                return jsonify("Não foi possível ler o código. Tente novamente."), 400
        else:
            return jsonify("Tipo de evidência inválido."), 400

        configured = next(
            entry
            for entry in self._configured_evidences(item)
            if entry["tipo"] == evidence_type
        )
        previous = SchedularTaskEvidence.query.filter_by(
            resposta_id=response.id,
            tipo=evidence_type,
        ).all()
        for evidence in previous:
            if evidence.tipo in file_types and evidence.valor:
                old_path = SCHEDULAR_EVIDENCE_DIR / Path(evidence.valor).name
                if old_path.is_file():
                    old_path.unlink()
            db.session.delete(evidence)
        db.session.add(
            SchedularTaskEvidence(
                resposta_id=response.id,
                tipo=evidence_type,
                valor=stored_value,
                obrigatoria=configured["obrigatoria"],
                coletada_por_colaborador_id=employee.id,
                coletada_em=self._now(),
            )
        )
        response.respondido_por_colaborador_id = employee.id
        response.respondido_em = self._now()
        db.session.commit()
        return jsonify({"message": "Evidência registrada.", "tarefa": self._task_payload(task)})

    @staticmethod
    def serve_task_evidence(evidence_id):
        evidence = db.session.get(SchedularTaskEvidence, evidence_id)
        if not evidence or evidence.tipo not in {"camera", "image", "signature"}:
            return jsonify("Evidência não encontrada."), 404
        safe_name = Path(evidence.valor).name
        if not safe_name or safe_name != evidence.valor:
            return jsonify("Evidência não encontrada."), 404
        return send_from_directory(SCHEDULAR_EVIDENCE_DIR, safe_name, as_attachment=False)

    def read_checklists(self):
        _, error = tmhub_admin_session()
        if error:
            return error
        rows = SchedularChecklist.query.order_by(SchedularChecklist.nome).all()
        return jsonify([self._checklist_payload(row) for row in rows])

    def create_checklist(self):
        _, error = tmhub_admin_session()
        if error:
            return error
        body = request.get_json(silent=True) or {}
        nome = str(body.get("nome") or "").strip()
        if not nome:
            return jsonify("Informe o nome do checklist."), 400
        checklist = SchedularChecklist(nome=nome, descricao=str(body.get("descricao") or "").strip() or None)
        db.session.add(checklist)
        db.session.flush()
        for index, item in enumerate(body.get("itens") or []):
            pergunta = str(item.get("pergunta") or "").strip()
            if pergunta:
                db.session.add(SchedularChecklistItem(checklist_id=checklist.id, pergunta=pergunta, tipo_resposta=item.get("tipo_resposta") or "texto", obrigatorio=bool(item.get("obrigatorio")), ordem=index, opcoes=item.get("opcoes") if isinstance(item.get("opcoes"), list) else [], evidencias=item.get("evidencias") if isinstance(item.get("evidencias"), list) else []))
        db.session.commit()
        return jsonify({"message": "Checklist criado com sucesso.", "checklist": self._checklist_payload(checklist)}), 201

    def update_checklist(self, checklist_id):
        _, error = tmhub_admin_session()
        if error:
            return error
        checklist = db.session.get(SchedularChecklist, checklist_id)
        if not checklist:
            return jsonify("Checklist nÃ£o encontrado."), 404
        body = request.get_json(silent=True) or {}
        nome = str(body.get("nome") or "").strip()
        if not nome:
            return jsonify("Informe o nome do checklist."), 400
        checklist.nome = nome
        checklist.descricao = str(body.get("descricao") or "").strip() or None
        if isinstance(body.get("itens"), list):
            current_items = {
                item.id: item
                for item in SchedularChecklistItem.query.filter_by(
                    checklist_id=checklist.id
                ).all()
            }
            kept_ids = set()
            for index, item in enumerate(body["itens"]):
                pergunta = str(item.get("pergunta") or "").strip()
                if not pergunta:
                    continue
                try:
                    item_id = int(item.get("id")) if item.get("id") else None
                except (TypeError, ValueError):
                    return jsonify("Identificador de item de checklist inválido."), 400
                row = current_items.get(item_id)
                if item_id and not row:
                    return jsonify("Um item informado não pertence a este checklist."), 400
                if not row:
                    row = SchedularChecklistItem(checklist_id=checklist.id)
                    db.session.add(row)
                else:
                    kept_ids.add(row.id)
                row.pergunta = pergunta
                row.tipo_resposta = item.get("tipo_resposta") or "texto"
                row.obrigatorio = bool(item.get("obrigatorio"))
                row.ordem = index
                row.opcoes = item.get("opcoes") if isinstance(item.get("opcoes"), list) else []
                row.evidencias = item.get("evidencias") if isinstance(item.get("evidencias"), list) else []
            removed_ids = set(current_items) - kept_ids
            if removed_ids and SchedularTaskResponse.query.filter(
                SchedularTaskResponse.checklist_item_id.in_(removed_ids)
            ).first():
                db.session.rollback()
                return jsonify("Não é possível remover um item que já possui respostas em tarefas. Mantenha-o para preservar o histórico."), 409
            if removed_ids:
                SchedularChecklistItem.query.filter(
                    SchedularChecklistItem.id.in_(removed_ids)
                ).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({"message": "Checklist atualizado com sucesso.", "checklist": self._checklist_payload(checklist)})

    def delete_checklist(self, checklist_id):
        _, error = tmhub_admin_session()
        if error:
            return error
        checklist = db.session.get(SchedularChecklist, checklist_id)
        if not checklist:
            return jsonify("Checklist nÃ£o encontrado."), 404
        active = SchedularRoutine.query.filter_by(checklist_id=checklist.id, ativa=True).first()
        if active:
            return jsonify("NÃ£o Ã© possÃ­vel excluir um checklist vinculado a uma rotina ativa."), 409
        db.session.delete(checklist)
        db.session.commit()
        return jsonify("Checklist excluÃ­do com sucesso.")
