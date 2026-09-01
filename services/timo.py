# Regras de negócio de assistente Timo.
# Biblioteca padrão.
import logging
import re
import unicodedata
from datetime import datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

# Dependências externas.
from flask import jsonify, request
from sqlalchemy import func, or_

# Módulos internos da aplicação.
from models.admissao import Vacancy
from models.centros_de_custo import CostCenters, DepartmentConfiguration
from models.colaboradores import Employees
from models.controle_faltas import AbsenceControl
from models.rp_historico import History
from models.rp_requisicao import Requisicao
from models.reservas_tecnicas import Floaters
from models.timo_aprendizados import TimoLearningExample
from models.timo_configuracoes import TimoCommandTrigger, TimoIntentConfiguration
from timo.analytics_catalog import ANALYTICS_INTENTS, analytics_intent_for_command
from timo.command_catalog import known_intent_for_command
from timo.entities import extract_entities, extract_period
from timo.navigation_catalog import (
    NAVIGATION_ACTION_PATHS,
    NAVIGATION_INTENTS,
    navigation_intent_for_command,
)
from timo.predictor import predictor
from timo.trainer import train as train_timo
from utils.db import db
from utils.filial_scope import apply_cost_center_scope, is_admin
from utils.permissions import has_permission
from utils.safe_route import safe_route


SAO_PAULO = ZoneInfo("America/Sao_Paulo")
logger = logging.getLogger(__name__)


class SafeTemplateValues(dict):
    """Mantém placeholders visíveis em vez de quebrar uma resposta configurada."""

    def __missing__(self, key):
        return "{" + key + "}"


class TimoCommandService:
    """Processa comandos e aplica a resposta/ação configurada por administradores."""

    # Limiar mínimo (20%) para aceitar a previsão estatística do modelo.
    # Os catálogos determinísticos continuam tendo prioridade antes daqui.
    MIN_CONFIDENCE = 0.20
    ACTION_NONE = "none"
    ACTION_NAVIGATE = "navigate"

    ACTION_PATHS = NAVIGATION_ACTION_PATHS

    INTENT_CATALOG = {
        "faltas_periodo": {
            "label": "Faltas no período",
            "description": "Mostra a quantidade de faltas no período falado.",
            "response": "Tivemos {total} falta(s) {period_label}.",
            "action_type": ACTION_NONE,
            "action_value": None,
        },
        "reposicoes_periodo": {
            "label": "Reposições no período",
            "description": "Mostra a quantidade de reposições concluídas no período falado.",
            "response": "Tivemos {total} reposição(ões) {period_label}.",
            "action_type": ACTION_NONE,
            "action_value": None,
        },
        "postos_descobertos": {
            "label": "Postos sem cobertura",
            "description": "Mostra quantas ocorrências ficaram sem cobertura.",
            "response": "{total} posto(s) ficaram sem cobertura {period_label}.",
            "action_type": ACTION_NONE,
            "action_value": None,
        },
        "vagas_abertas": {
            "label": "Vagas abertas",
            "description": "Mostra a quantidade atual de vagas abertas.",
            "response": "Existem {total} vaga(s) aberta(s).",
            "action_type": ACTION_NONE,
            "action_value": None,
        },
        **ANALYTICS_INTENTS,
        **NAVIGATION_INTENTS,
    }

    TEMPLATE_VARIABLES = {
        "faltas_periodo": ["{total}", "{period_label}"],
        "reposicoes_periodo": ["{total}", "{period_label}"],
        "postos_descobertos": ["{total}", "{period_label}"],
        "vagas_abertas": ["{total}"],
        **{
            intent: definition["variables"]
            for intent, definition in ANALYTICS_INTENTS.items()
        },
    }

    ANALYTICS_INTENT_IDS = {
        "faltas_periodo",
        "reposicoes_periodo",
        "postos_descobertos",
        "vagas_abertas",
        *ANALYTICS_INTENTS.keys(),
    }

    @staticmethod
    def _normalize(value):
        text = unicodedata.normalize("NFD", str(value or "").strip().lower())
        text = "".join(character for character in text if not unicodedata.combining(character))
        return re.sub(r"\s+", " ", text)

    @classmethod
    def _ensure_defaults(cls):
        current = {
            row.intent: row
            for row in TimoIntentConfiguration.query.filter(
                TimoIntentConfiguration.intent.in_(cls.INTENT_CATALOG)
            ).all()
        }
        created = False
        for intent, definition in cls.INTENT_CATALOG.items():
            if intent in current:
                continue
            row = TimoIntentConfiguration(
                intent=intent,
                titulo=definition["label"],
                descricao=definition["description"],
                personalizado=False,
                ativo=True,
                resposta_template=definition["response"],
                acao_tipo=definition["action_type"],
                acao_valor=definition["action_value"],
            )
            db.session.add(row)
            current[intent] = row
            created = True
        if created:
            db.session.commit()
        return current

    @classmethod
    def _serialize_configuration(cls, row, definition=None):
        definition = definition or {}
        return {
            "intent": row.intent,
            "label": row.titulo or definition.get("label") or row.intent,
            "description": row.descricao or definition.get("description") or "Comando configurado pelo administrador.",
            "variaveis": cls.TEMPLATE_VARIABLES.get(row.intent, []),
            "personalizado": bool(row.personalizado),
            "comandos": [command.frase for command in row.comandos],
            "ativo": bool(row.ativo),
            "resposta_template": row.resposta_template or definition.get("response") or "Comando concluído.",
            "acao_tipo": row.acao_tipo or cls.ACTION_NONE,
            "acao_valor": row.acao_valor,
            "categoria": (
                "personalizado"
                if row.personalizado
                else "analises"
                if row.intent in cls.ANALYTICS_INTENT_IDS
                else "telas"
            ),
        }

    @classmethod
    def _serialize_learning(cls, item):
        return {
            "id": item.id,
            "texto": item.texto_normalizado,
            "intent_sugerida": item.intent_sugerida,
            "confianca": item.confianca,
            "status": item.status,
            "intent_confirmada": item.intent_confirmada,
            "ocorrencias": item.ocorrencias,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }

    @classmethod
    def _emit_learning_update(cls, event, item=None):
        """Sincroniza a fila de aprendizado aberta pelo administrador."""
        from utils.socket import socketio

        payload = {
            "event": event,
            "aprendizado": cls._serialize_learning(item) if item else None,
            "aprendizados_aprovados": TimoLearningExample.query.filter_by(
                status="aprovado"
            ).count(),
        }
        # A revisão pertence aos administradores. A sala por role garante que
        # frases enviadas por qualquer usuário apareçam na fila sem recarregar.
        socketio.emit("timo_learning_updated", payload, to="role:admin")

    @classmethod
    def _capture_learning_candidate(cls, command, prediction, token_data):
        """Registra somente comandos não entendidos; não há treinamento automático."""
        existing = TimoLearningExample.query.filter_by(
            texto_normalizado=command,
            status="pendente",
        ).first()
        now = datetime.now(SAO_PAULO)
        if existing:
            existing.ocorrencias += 1
            existing.intent_sugerida = prediction.get("intent") or existing.intent_sugerida
            existing.confianca = prediction.get("confidence")
            existing.ultimo_recebido_em = now
            item = existing
        else:
            item = TimoLearningExample(
                texto_normalizado=command,
                intent_sugerida=prediction.get("intent"),
                confianca=prediction.get("confidence"),
                criado_por_usuario_id=(token_data or {}).get("id"),
                ultimo_recebido_em=now,
            )
            db.session.add(item)
        db.session.commit()
        cls._emit_learning_update("capturado", item)

    @staticmethod
    def _should_capture_learning(token_data):
        """Aceita texto autenticado da interface ou voz com wake word validada."""
        channel = str(request.headers.get("X-Timo-Channel") or "").strip().lower()
        is_voice_agent = (token_data or {}).get("typ") == "timo_voice_agent"
        is_web_text = channel == "web-text" and not is_voice_agent
        wake_verified = request.headers.get("X-Timo-Wake-Verified") == "1"
        return is_web_text or wake_verified

    @classmethod
    def _trained_learning_intent_for_command(cls, command):
        """Resolve literalmente as frases já revisadas e treinadas.

        Isto impede que uma frase idêntica volte para a fila e garante um
        resultado igual em todos os workers logo após o treinamento.
        """
        item = TimoLearningExample.query.filter_by(
            texto_normalizado=command,
            status="treinado",
        ).filter(
            TimoLearningExample.intent_confirmada.isnot(None)
        ).order_by(TimoLearningExample.revisado_em.desc()).first()
        return item.intent_confirmada if item else None

    @classmethod
    def _custom_configuration_for_command(cls, command):
        trigger = TimoCommandTrigger.query.filter_by(frase_normalizada=command).first()
        return trigger.configuracao if trigger and trigger.configuracao.personalizado else None

    @classmethod
    def _configured_intent(cls, intent):
        row = TimoIntentConfiguration.query.filter_by(intent=intent).first()
        if row:
            return row
        definition = cls.INTENT_CATALOG.get(intent)
        if not definition:
            return None
        return TimoIntentConfiguration(
            intent=intent,
            ativo=True,
            resposta_template=definition["response"],
            acao_tipo=definition["action_type"],
            acao_valor=definition["action_value"],
        )

    @classmethod
    def _validate_action(cls, action_type, action_value):
        if action_type not in {cls.ACTION_NONE, cls.ACTION_NAVIGATE}:
            return None, None, "Tipo de ação inválido."
        if action_type == cls.ACTION_NONE:
            return action_type, None, None
        value = str(action_value or "").strip()
        if value not in cls.ACTION_PATHS:
            return None, None, "Selecione uma tela válida para a navegação."
        return action_type, value, None

    @staticmethod
    def _period_range(period):
        start_date = datetime.fromisoformat(period["start"]).date()
        end_date = datetime.fromisoformat(period["end"]).date()
        return datetime.combine(start_date, time.min), datetime.combine(end_date, time.max)

    @staticmethod
    def _absence_reason_filter():
        """Mantém férias, remanejamento e posto vago fora dos indicadores de falta."""
        return ~func.upper(AbsenceControl.motivo).in_(
            ("REMANEJAMENTO", "FERIAS", "FÉRIAS", "POSTO VAGO")
        )

    @staticmethod
    def _latest_history_query():
        latest_history = (
            db.session.query(
                History.requisicao_id,
                func.max(History.id).label("history_id"),
            )
            .group_by(History.requisicao_id)
            .subquery()
        )
        return History.query.join(latest_history, History.id == latest_history.c.history_id)

    @staticmethod
    def _active_headcount(token_data):
        query = Employees.query.filter(Employees.situacao == 1)
        return apply_cost_center_scope(query, Employees.centro_id, token_data).count()

    @classmethod
    def _absenteeism_data(cls, entities, token_data):
        start, end = cls._period_range(entities["period"])
        absence_query = AbsenceControl.query.filter(
            AbsenceControl.data_falta.between(start, end),
            cls._absence_reason_filter(),
        )
        absences = apply_cost_center_scope(
            absence_query, AbsenceControl.centro_custo_id, token_data
        ).count()
        active_headcount = cls._active_headcount(token_data)
        start_date, end_date = start.date(), end.date()
        operational_days = sum(
            1
            for day in range((end_date - start_date).days + 1)
            if (start_date + timedelta(days=day)).weekday() < 5
        ) or 1
        average_absences = absences / operational_days
        rate = (average_absences / active_headcount * 100) if active_headcount else 0
        return {
            "period_label": entities["period"]["label"],
            "faltas": absences,
            "media_faltas_dia": round(average_absences, 2),
            "percentual_absenteismo": round(rate, 2),
            "quadro_ativo": active_headcount,
        }

    @classmethod
    def _coverage_data(cls, entities, token_data):
        start, end = cls._period_range(entities["period"])
        history_query = cls._latest_history_query().filter(
            History.created_at.between(start, end),
            History.status.in_(("approved", "reproved")),
        )
        history_query = apply_cost_center_scope(history_query, History.cc, token_data)
        covered = history_query.filter(History.reserva_id > 0).count()
        uncovered = history_query.filter(
            or_(History.reserva_id == 0, History.reserva_id.is_(None))
        ).count()
        open_query = Requisicao.query.filter(
            Requisicao.created_at.between(start, end),
            Requisicao.status.in_(("pending", "updated")),
        )
        open_requests = apply_cost_center_scope(open_query, Requisicao.cc, token_data).count()
        decided = covered + uncovered
        rate = (covered / decided * 100) if decided else 0
        return {
            "period_label": entities["period"]["label"],
            "cobertas": covered,
            "descobertas": uncovered,
            "abertas": open_requests,
            "taxa_cobertura": round(rate, 2),
        }

    @classmethod
    def _pending_absences_data(cls, token_data):
        pending_query = AbsenceControl.query.filter(
            AbsenceControl.status == "pendente",
            cls._absence_reason_filter(),
        )
        pending_query = apply_cost_center_scope(
            pending_query, AbsenceControl.centro_custo_id, token_data
        )
        now = datetime.now(SAO_PAULO)
        overdue = pending_query.filter(
            AbsenceControl.prazo_atestado.isnot(None),
            AbsenceControl.prazo_atestado < now,
        ).count()
        return {"pendentes": pending_query.count(), "atrasadas": overdue}

    @staticmethod
    def _lotation_rows(token_data):
        active_by_center = (
            db.session.query(
                Employees.centro_id.label("centro_id"),
                func.count(Employees.id).label("ativos"),
            )
            .filter(Employees.situacao == 1)
            .group_by(Employees.centro_id)
            .subquery()
        )
        query = (
            db.session.query(
                CostCenters.departamento.label("departamento"),
                DepartmentConfiguration.capacidade_pessoas,
                func.coalesce(func.sum(active_by_center.c.ativos), 0).label("ativos"),
            )
            .outerjoin(active_by_center, active_by_center.c.centro_id == CostCenters.id)
            .outerjoin(
                DepartmentConfiguration,
                DepartmentConfiguration.departamento == CostCenters.departamento,
            )
            .group_by(CostCenters.departamento, DepartmentConfiguration.capacidade_pessoas)
        )
        return apply_cost_center_scope(query, CostCenters.id, token_data).all()

    @classmethod
    def _lotation_data(cls, token_data):
        rows = cls._lotation_rows(token_data)
        planned = [row for row in rows if row.capacidade_pessoas is not None]
        capacity = sum(int(row.capacidade_pessoas) for row in planned)
        active = sum(int(row.ativos or 0) for row in planned)
        deficit = sum(max(0, int(row.capacidade_pessoas) - int(row.ativos or 0)) for row in planned)
        excess = sum(max(0, int(row.ativos or 0) - int(row.capacidade_pessoas)) for row in planned)
        critical = sorted(
            (
                (f"DPTO. {row.departamento}", int(row.capacidade_pessoas) - int(row.ativos or 0))
                for row in planned
                if int(row.capacidade_pessoas) > int(row.ativos or 0)
            ),
            key=lambda item: item[1],
            reverse=True,
        )[:3]
        critical_text = (
            "Contratos com maior déficit: "
            + "; ".join(f"{name} ({gap} posição(ões))" for name, gap in critical)
            if critical
            else "Não há contratos com déficit no QL informado."
        )
        return {
            "quadro_ativo": active,
            "capacidade_planejada": capacity,
            "centros_planejados": len(planned),
            "centros_sem_capacidade": len(rows) - len(planned),
            "deficit": deficit,
            "excedente": excess,
            "qtd_criticos": len(critical),
            "contratos_criticos": critical_text,
        }

    @classmethod
    def _intent_data(cls, intent, entities, token_data):
        if intent == "absenteismo_periodo":
            if not (
                has_permission(token_data, "dashboard_faltas", "view")
                or has_permission(token_data, "controle_faltas", "view")
            ):
                return None, "Você não possui acesso aos dados de faltas."
            return cls._absenteeism_data(entities, token_data), None

        if intent == "coberturas_periodo":
            if not has_permission(token_data, "reposicoes", "view"):
                return None, "Você não possui acesso aos dados de reposições."
            return cls._coverage_data(entities, token_data), None

        if intent == "faltas_pendentes":
            if not has_permission(token_data, "controle_faltas", "view"):
                return None, "Você não possui acesso ao Controle de Faltas."
            return cls._pending_absences_data(token_data), None

        if intent in {"quadro_lotacao", "quadro_lotacao_critico"}:
            if not has_permission(token_data, "estrutura", "view"):
                return None, "Você não possui acesso à Estrutura e ao quadro de lotação."
            return cls._lotation_data(token_data), None

        if intent == "reservas_disponiveis":
            if not has_permission(token_data, "reservas", "view"):
                return None, "Você não possui acesso às reservas técnicas."
            query = Floaters.query.join(Employees, Employees.id == Floaters.employee_id).filter(
                Floaters.disponivel.is_(True)
            )
            total = apply_cost_center_scope(query, Employees.centro_id, token_data).count()
            return {"total": total}, None

        if intent == "faltas_periodo":
            if not (
                has_permission(token_data, "dashboard_faltas", "view")
                or has_permission(token_data, "controle_faltas", "view")
            ):
                return None, "Você não possui acesso aos dados de faltas."
            start, end = cls._period_range(entities["period"])
            query = AbsenceControl.query.filter(AbsenceControl.data_falta.between(start, end))
            total = apply_cost_center_scope(query, AbsenceControl.centro_custo_id, token_data).count()
            return {"total": total, "period_label": entities["period"]["label"]}, None

        if intent in {"reposicoes_periodo", "postos_descobertos"}:
            if not has_permission(token_data, "reposicoes", "view"):
                return None, "Você não possui acesso aos dados de reposições."
            start, end = cls._period_range(entities["period"])
            query = History.query.filter(History.created_at.between(start, end))
            if intent == "reposicoes_periodo":
                query = query.filter(History.reserva_id != 0)
            else:
                query = query.filter(or_(History.reserva_id == 0, History.reserva_id.is_(None)))
            total = apply_cost_center_scope(query, History.cc, token_data).count()
            return {"total": total, "period_label": entities["period"]["label"]}, None

        if intent == "vagas_abertas":
            if not has_permission(token_data, "admissoes", "view"):
                return None, "Você não possui acesso às vagas."
            query = Vacancy.query.filter(func.lower(Vacancy.status) == "aberta")
            total = apply_cost_center_scope(query, Vacancy.centro_custo_id, token_data).count()
            return {"total": total}, None

        return {}, None

    @classmethod
    def _response_text(cls, template, data, fallback):
        text = str(template or fallback or "Comando concluído.").strip()
        try:
            return text.format_map(SafeTemplateValues(data or {}))
        except (KeyError, ValueError):
            return fallback or "Comando concluído."

    @classmethod
    def _action_for_user(cls, configuration, token_data):
        if configuration.acao_tipo != cls.ACTION_NAVIGATE:
            return None
        path = configuration.acao_valor
        metadata = cls.ACTION_PATHS.get(path)
        if not metadata:
            return None
        if metadata.get("admin_only") and not is_admin(token_data):
            return None
        permission = metadata.get("permission")
        if permission and not has_permission(token_data, permission, "view"):
            return None
        return {"type": cls.ACTION_NAVIGATE, "path": path}

    @safe_route
    def process(self, token_data):
        if token_data.get("typ") == "timo_voice_agent":
            try:
                from services.timo_voice_agents import validate_agent_token
                agent, _ = validate_agent_token(request.headers.get("Access-Token"))
                if int(agent.usuario_id) != int(token_data.get("id")):
                    return jsonify("Credencial do Timo Voice Agent inválida."), 403
            except Exception:
                return jsonify("Credencial do Timo Voice Agent inválida ou revogada."), 401
        body = request.get_json(silent=True) or {}
        command = self._normalize(body.get("text") or body.get("command"))
        if not command:
            return jsonify({"success": False, "message": "Não entendi o comando.", "action": None}), 400
        if len(command) > 500:
            return jsonify({"success": False, "message": "Esse comando é muito longo.", "action": None}), 400

        custom_configuration = self._custom_configuration_for_command(command)
        navigation_intent = None if custom_configuration else navigation_intent_for_command(command)
        analytics_intent = (
            None
            if custom_configuration or navigation_intent
            else analytics_intent_for_command(command)
        )
        trained_learning_intent = (
            None
            if custom_configuration or navigation_intent or analytics_intent
            else self._trained_learning_intent_for_command(command)
        )
        known_command = (
            None
            if custom_configuration or navigation_intent or analytics_intent or trained_learning_intent
            else known_intent_for_command(command)
        )
        prediction = (
            predictor.predict(command)
            if not custom_configuration and not navigation_intent and not analytics_intent
            and not trained_learning_intent and not known_command
            else None
        )
        intent = (
            custom_configuration.intent
            if custom_configuration
            else navigation_intent or analytics_intent or trained_learning_intent
            or (known_command or {}).get("intent") or prediction["intent"]
        )
        confidence = (
            1.0
            if custom_configuration or navigation_intent or analytics_intent or trained_learning_intent or known_command
            else prediction["confidence"]
        )
        definition = self.INTENT_CATALOG.get(intent)
        if not custom_configuration and (confidence < self.MIN_CONFIDENCE or not definition):
            try:
                # Texto digitado na interface já é uma tentativa explícita de
                # comando. No agente local, a wake word continua obrigatória.
                if self._should_capture_learning(token_data):
                    self._capture_learning_candidate(command, prediction or {}, token_data)
            except Exception:
                db.session.rollback()
                logger.exception("Falha ao registrar frase não reconhecida do Timo")
            return jsonify({
                "success": False,
                "understood": False,
                "intent": intent,
                "confidence": confidence,
                "message": "Ainda não reconheci esse comando.",
                "action": None,
            }), 200

        configuration = custom_configuration or self._configured_intent(intent)
        if not configuration.ativo:
            return jsonify({
                "success": False,
                "understood": True,
                "intent": intent,
                "confidence": confidence,
                "message": "Essa automação está desativada nas configurações do Timo.",
                "action": None,
            }), 200

        entities = extract_entities(command, intent) if definition else {}
        if intent in {"absenteismo_periodo", "coberturas_periodo"} and "period" not in entities:
            entities["period"] = extract_period(command)
        data, error = self._intent_data(intent, entities, token_data) if definition else ({}, None)
        if error:
            return jsonify({"success": False, "message": error, "action": None}), 403
        action = self._action_for_user(configuration, token_data)
        return jsonify({
            "success": True,
            "understood": True,
            "intent": intent,
            "confidence": confidence,
            "entities": entities,
            "data": data,
            "message": self._response_text(
                configuration.resposta_template,
                data,
                definition["response"] if definition else "Comando concluído.",
            ),
            "action": action,
        }), 200

    @safe_route
    def read_configurations(self, token_data):
        if not is_admin(token_data):
            return jsonify("A configuração do Timo está disponível apenas para administradores."), 403
        rows = self._ensure_defaults()
        custom_rows = TimoIntentConfiguration.query.filter_by(personalizado=True).order_by(
            TimoIntentConfiguration.created_at.desc()
        ).all()
        return jsonify({
            "configuracoes": [
                self._serialize_configuration(rows[intent], definition)
                for intent, definition in self.INTENT_CATALOG.items()
            ] + [self._serialize_configuration(row) for row in custom_rows],
            "acoes": self.action_options(),
            "aprendizados": [
                self._serialize_learning(item)
                for item in TimoLearningExample.query.filter_by(status="pendente")
                .order_by(TimoLearningExample.ocorrencias.desc(), TimoLearningExample.updated_at.desc())
                .limit(100)
                .all()
            ],
            "aprendizados_aprovados": TimoLearningExample.query.filter_by(
                status="aprovado"
            ).count(),
            "aprendizados_treinados": TimoLearningExample.query.filter_by(
                status="treinado"
            ).count(),
            "intents_disponiveis": [
                {
                    "label": definition["label"],
                    "value": intent,
                    "categoria": "analises" if intent in self.ANALYTICS_INTENT_IDS else "telas",
                }
                for intent, definition in self.INTENT_CATALOG.items()
            ],
        }), 200

    @safe_route
    def review_learning(self, token_data, learning_id):
        if not is_admin(token_data):
            return jsonify("A configuração do Timo está disponível apenas para administradores."), 403
        item = db.session.get(TimoLearningExample, learning_id)
        if not item:
            return jsonify("Frase de aprendizado não encontrada."), 404
        body = request.get_json(silent=True) or {}
        status = str(body.get("status") or "").strip().lower()
        if status not in {"aprovado", "ignorado"}:
            return jsonify("Informe se a frase deve ser aprovada ou ignorada."), 400
        intent = str(body.get("intent") or "").strip()
        if status == "aprovado" and intent not in self.INTENT_CATALOG:
            return jsonify("Selecione uma intenção válida para treinar."), 400
        item.status = status
        item.intent_confirmada = intent if status == "aprovado" else None
        item.revisado_por_usuario_id = token_data.get("id")
        item.revisado_em = datetime.now(SAO_PAULO)
        db.session.commit()
        self._emit_learning_update("revisado", item)
        return jsonify({"message": "Frase revisada.", "aprendizado": self._serialize_learning(item)}), 200

    @safe_route
    def train_learning(self, token_data):
        if not is_admin(token_data):
            return jsonify("O treinamento do Timo está disponível apenas para administradores."), 403
        approved = TimoLearningExample.query.filter_by(status="aprovado").all()
        examples = [
            {"text": item.texto_normalizado, "intent": item.intent_confirmada}
            for item in approved
            if item.intent_confirmada in self.INTENT_CATALOG
        ]
        try:
            train_timo(examples)
            predictor.reload()
        except OSError:
            # O modelo publicado em timo/models é imutável no servidor. O
            # treinamento usa storage/timo; este retorno preserva uma mensagem
            # útil se o diretório persistente for configurado incorretamente.
            return jsonify(
                "Não foi possível salvar o modelo treinado do Timo. "
                "Verifique a permissão do diretório de armazenamento da API."
            ), 500
        approved_ids = [
            item.id
            for item in approved
            if item.intent_confirmada in self.INTENT_CATALOG
        ]
        if approved_ids:
            TimoLearningExample.query.filter(
                TimoLearningExample.id.in_(approved_ids)
            ).update({"status": "treinado"}, synchronize_session=False)
            db.session.commit()
        self._emit_learning_update("treinado")
        return jsonify({
            "message": "Modelo do Timo treinado com as frases revisadas.",
            "frases_treinadas": len(examples),
            "aprendizados_aprovados": 0,
        }), 200

    @safe_route
    def update_configuration(self, token_data, intent):
        if not is_admin(token_data):
            return jsonify("A configuração do Timo está disponível apenas para administradores."), 403
        row = TimoIntentConfiguration.query.filter_by(intent=intent).first()
        if intent not in self.INTENT_CATALOG and not (row and row.personalizado):
            return jsonify("Intenção do Timo não encontrada."), 404

        body = request.get_json(silent=True) or {}
        template = str(body.get("resposta_template") or "").strip()
        if not template or len(template) > 1000:
            return jsonify("A resposta deve ter entre 1 e 1000 caracteres."), 400
        action_type, action_value, error = self._validate_action(
            str(body.get("acao_tipo") or self.ACTION_NONE).strip().lower(),
            body.get("acao_valor"),
        )
        if error:
            return jsonify(error), 400

        if not row:
            definition = self.INTENT_CATALOG[intent]
            row = TimoIntentConfiguration(
                intent=intent,
                titulo=definition["label"],
                descricao=definition["description"],
                personalizado=False,
            )
            db.session.add(row)
        row.ativo = bool(body.get("ativo", True))
        row.resposta_template = template
        row.acao_tipo = action_type
        row.acao_valor = action_value
        row.atualizado_por_usuario_id = token_data.get("id")
        db.session.commit()
        return jsonify({"message": "Configuração do Timo atualizada."}), 200

    @safe_route
    def create_custom_command(self, token_data):
        if not is_admin(token_data):
            return jsonify("A configuração do Timo está disponível apenas para administradores."), 403

        body = request.get_json(silent=True) or {}
        title = str(body.get("titulo") or "").strip()
        command = str(body.get("comando") or "").strip()
        normalized_command = self._normalize(command)
        template = str(body.get("resposta_template") or "").strip()
        description = str(body.get("descricao") or "").strip()
        if not 2 <= len(title) <= 150:
            return jsonify("Informe um nome entre 2 e 150 caracteres."), 400
        if not 2 <= len(normalized_command) <= 500:
            return jsonify("Informe uma frase de comando entre 2 e 500 caracteres."), 400
        if TimoCommandTrigger.query.filter_by(frase_normalizada=normalized_command).first():
            return jsonify("Essa frase de comando já está cadastrada."), 409
        if not template or len(template) > 1000:
            return jsonify("A resposta deve ter entre 1 e 1000 caracteres."), 400
        action_type, action_value, error = self._validate_action(
            str(body.get("acao_tipo") or self.ACTION_NONE).strip().lower(),
            body.get("acao_valor"),
        )
        if error:
            return jsonify(error), 400

        configuration = TimoIntentConfiguration(
            intent=f"custom_{uuid4().hex[:12]}",
            titulo=title,
            descricao=description or "Automação personalizada.",
            personalizado=True,
            ativo=bool(body.get("ativo", True)),
            resposta_template=template,
            acao_tipo=action_type,
            acao_valor=action_value,
            atualizado_por_usuario_id=token_data.get("id"),
        )
        db.session.add(configuration)
        db.session.flush()
        db.session.add(TimoCommandTrigger(
            configuracao_id=configuration.id,
            frase=command,
            frase_normalizada=normalized_command,
        ))
        db.session.commit()
        return jsonify({
            "message": "Comando do Timo criado.",
            "configuracao": self._serialize_configuration(configuration),
        }), 201

    @safe_route
    def delete_custom_command(self, token_data, intent):
        if not is_admin(token_data):
            return jsonify("A configuração do Timo está disponível apenas para administradores."), 403
        configuration = TimoIntentConfiguration.query.filter_by(
            intent=intent,
            personalizado=True,
        ).first()
        if not configuration:
            return jsonify("Comando personalizado não encontrado."), 404
        db.session.delete(configuration)
        db.session.commit()
        return jsonify({"message": "Comando do Timo removido."}), 200

    @classmethod
    def action_options(cls):
        return [
            {"label": metadata["label"], "value": path}
            for path, metadata in cls.ACTION_PATHS.items()
        ]
