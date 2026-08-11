import re
import unicodedata
from datetime import datetime, time
from uuid import uuid4
from zoneinfo import ZoneInfo

from flask import jsonify, request
from sqlalchemy import func, or_

from models.admissao import Vacancy
from models.controle_faltas import AbsenceControl
from models.rp_historico import History
from models.timo_configuracoes import TimoCommandTrigger, TimoIntentConfiguration
from timo.entities import extract_entities
from timo.predictor import predictor
from utils.db import db
from utils.filial_scope import apply_cost_center_scope, is_admin
from utils.permissions import has_permission
from utils.safe_route import safe_route


SAO_PAULO = ZoneInfo("America/Sao_Paulo")


class SafeTemplateValues(dict):
    """Mantém placeholders visíveis em vez de quebrar uma resposta configurada."""

    def __missing__(self, key):
        return "{" + key + "}"


class TimoCommandService:
    """Processa comandos e aplica a resposta/ação configurada por administradores."""

    MIN_CONFIDENCE = 0.30
    ACTION_NONE = "none"
    ACTION_NAVIGATE = "navigate"

    ACTION_PATHS = {
        "/controle-faltas": {
            "label": "Controle de Faltas",
            "permission": "controle_faltas",
        },
        "/reposicoes/requisicoes": {
            "label": "Requisições",
            "permission": "reposicoes",
        },
        "/reposicoes/reservas": {
            "label": "Reservas técnicas",
            "permission": "reservas",
        },
        "/projetos": {
            "label": "Meus Projetos",
            "permission": "projetos",
        },
        "/estoque/produtos": {
            "label": "Produtos em estoque",
            "permission": "estoque_produtos",
        },
        "/reports/colaboradores-departamento": {
            "label": "Colaboradores por departamento",
            "permission": "dashboard_colaboradores",
        },
        "/admissao": {
            "label": "Vagas e admissões",
            "permission": "admissoes",
        },
    }

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
        "navegar_faltas": {
            "label": "Abrir Controle de Faltas",
            "description": "Abre a tela do Controle de Faltas.",
            "response": "Abrindo o Controle de Faltas.",
            "action_type": ACTION_NAVIGATE,
            "action_value": "/controle-faltas",
        },
        "navegar_colaboradores": {
            "label": "Abrir Colaboradores por departamento",
            "description": "Abre a tela de colaboradores por departamento.",
            "response": "Abrindo Colaboradores por departamento.",
            "action_type": ACTION_NAVIGATE,
            "action_value": "/reports/colaboradores-departamento",
        },
    }

    TEMPLATE_VARIABLES = {
        "faltas_periodo": ["{total}", "{period_label}"],
        "reposicoes_periodo": ["{total}", "{period_label}"],
        "postos_descobertos": ["{total}", "{period_label}"],
        "vagas_abertas": ["{total}"],
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
        }

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

    @classmethod
    def _intent_data(cls, intent, entities, token_data):
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
        if not metadata or not has_permission(token_data, metadata["permission"], "view"):
            return None
        return {"type": cls.ACTION_NAVIGATE, "path": path}

    @safe_route
    def process(self, token_data):
        body = request.get_json(silent=True) or {}
        command = self._normalize(body.get("text") or body.get("command"))
        if not command:
            return jsonify({"success": False, "message": "Não entendi o comando.", "action": None}), 400
        if len(command) > 500:
            return jsonify({"success": False, "message": "Esse comando é muito longo.", "action": None}), 400

        custom_configuration = self._custom_configuration_for_command(command)
        prediction = predictor.predict(command) if not custom_configuration else None
        intent = custom_configuration.intent if custom_configuration else prediction["intent"]
        confidence = 1.0 if custom_configuration else prediction["confidence"]
        definition = self.INTENT_CATALOG.get(intent)
        if not custom_configuration and (confidence < self.MIN_CONFIDENCE or not definition):
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
