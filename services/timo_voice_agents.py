# Regras de negócio de agentes de voz do Timo.
"""Pareamento, credenciais e controle do Timo Voice Agent."""

# Biblioteca padrão.
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from os import getenv
from secrets import token_urlsafe
from uuid import uuid4

# Dependências externas.
from flask import jsonify, request
from jwt import decode, encode

# Módulos internos da aplicação.
from models.timo_voice_agents import TimoUserPreference, TimoVoiceAgent, TimoVoicePairing
from models.usuarios import Users
from utils.db import db
from utils.filial_scope import is_admin
from utils.safe_route import safe_route


PAIRING_TTL_MINUTES = 10
AGENT_TOKEN_TTL_DAYS = 30


def _now():
    return datetime.now(timezone.utc)


def _hash(value):
    return sha256(str(value).encode("utf-8")).hexdigest()


def issue_agent_token(agent):
    user = db.session.get(Users, agent.usuario_id)
    return encode(
        {
            "typ": "timo_voice_agent",
            "agent_id": agent.id,
            "id": agent.usuario_id,
            "ver": agent.token_version,
            "usr_ver": int(user.token_version or 0) if user else -1,
            "exp": _now() + timedelta(days=AGENT_TOKEN_TTL_DAYS),
        },
        getenv("SECRET"),
        algorithm="HS256",
    )


def validate_agent_token(token):
    payload = decode(token, getenv("SECRET"), algorithms=["HS256"])
    if payload.get("typ") != "timo_voice_agent":
        raise ValueError("Token do agente inválido.")
    agent = db.session.get(TimoVoiceAgent, payload.get("agent_id"))
    if not agent or not agent.ativo:
        raise ValueError("Agente indisponível.")
    if int(payload.get("id") or 0) != int(agent.usuario_id):
        raise ValueError("Vínculo do agente inválido.")
    if int(payload.get("ver", -1)) != int(agent.token_version or 0):
        raise ValueError("Credencial do agente foi revogada.")
    user = db.session.get(Users, agent.usuario_id)
    if not user or int(payload.get("usr_ver", -1)) != int(user.token_version or 0):
        raise ValueError("A sessão do proprietário foi invalidada.")
    return agent, payload


class TimoVoiceAgentService:
    @staticmethod
    def _require_admin(token_data):
        if not is_admin(token_data):
            return jsonify("O Timo Voice Agent está disponível somente para administradores."), 403
        return None

    @staticmethod
    def _preference(user_id):
        preference = db.session.get(TimoUserPreference, user_id)
        if not preference:
            preference = TimoUserPreference(usuario_id=user_id)
            db.session.add(preference)
            db.session.flush()
        return preference

    @staticmethod
    def _serialize(agent, preference=None):
        from utils.timo_voice_socket import is_agent_online

        return {
            "id": agent.id,
            "nome": agent.nome,
            "dispositivo_id": agent.dispositivo_id,
            "ativo": bool(agent.ativo),
            "online": is_agent_online(agent.id),
            "estado": agent.ultimo_estado or "desconectado",
            "ultimo_heartbeat_em": agent.ultimo_heartbeat_em.isoformat() if agent.ultimo_heartbeat_em else None,
            "preferido": bool(preference and preference.agente_preferido_id == agent.id),
        }

    def agent_theme(self):
        """Endpoint exclusivo do agente pareado para aplicar a paleta do dono."""
        token = request.headers.get("Access-Token")
        if not token:
            return jsonify("Credencial do agente obrigatória."), 401
        try:
            agent, _ = validate_agent_token(token)
        except Exception:
            return jsonify("Credencial do agente inválida."), 401
        user = db.session.get(Users, agent.usuario_id)
        if not user:
            return jsonify("Usuário do agente não encontrado."), 404
        return jsonify({
            "tema": user.tema or "tmhub",
            "modo_tema": user.modo_tema or "light",
        }), 200

    @safe_route
    def list(self, token_data):
        forbidden = self._require_admin(token_data)
        if forbidden:
            return forbidden
        user_id = token_data.get("id")
        preference = self._preference(user_id)
        agents = TimoVoiceAgent.query.filter_by(usuario_id=user_id).order_by(
            TimoVoiceAgent.created_at.desc()
        ).all()
        return jsonify({
            "agentes": [self._serialize(agent, preference) for agent in agents],
            "preferencias": {
                "habilitado": bool(preference.habilitado),
                "agente_preferido_id": preference.agente_preferido_id,
                "skin": preference.skin,
                "tema_balao": preference.tema_balao,
            },
        }), 200

    @safe_route
    def create_pairing(self, token_data):
        forbidden = self._require_admin(token_data)
        if forbidden:
            return forbidden
        code = token_urlsafe(32)
        pairing = TimoVoicePairing(
            usuario_id=token_data.get("id"),
            codigo_hash=_hash(code),
            expira_em=_now() + timedelta(minutes=PAIRING_TTL_MINUTES),
        )
        db.session.add(pairing)
        db.session.commit()
        return jsonify({
            "codigo": code,
            "expira_em": pairing.expira_em.isoformat(),
            "instrucoes": "Cole este código no Timo Voice Agent. Ele expira em 10 minutos e só pode ser usado uma vez.",
        }), 201

    def pair(self):
        body = request.get_json(silent=True) or {}
        code = str(body.get("codigo") or "").strip()
        device_id = str(body.get("dispositivo_id") or "").strip()
        name = str(body.get("nome") or "Timo Voice Agent").strip()[:120]
        if len(code) < 24 or not device_id or len(device_id) > 128:
            return jsonify("Código de pareamento ou identificador do dispositivo inválido."), 400
        pairing = TimoVoicePairing.query.filter_by(codigo_hash=_hash(code)).first()
        if not pairing or pairing.utilizado_em or pairing.expira_em < _now():
            return jsonify("Código de pareamento inválido, utilizado ou expirado."), 400

        agent = TimoVoiceAgent.query.filter_by(dispositivo_id=device_id).first()
        if agent and agent.usuario_id != pairing.usuario_id:
            return jsonify("Este dispositivo já está vinculado a outra conta."), 409
        if not agent:
            agent = TimoVoiceAgent(
                id=str(uuid4()),
                usuario_id=pairing.usuario_id,
                dispositivo_id=device_id,
                nome=name or "Timo Voice Agent",
            )
            db.session.add(agent)
        else:
            agent.nome = name or agent.nome
            agent.ativo = True
            agent.token_version += 1
        pairing.utilizado_em = _now()
        pairing.agente_id = agent.id
        preference = self._preference(pairing.usuario_id)
        preference.agente_preferido_id = agent.id
        db.session.commit()
        return jsonify({
            "agente": self._serialize(agent, preference),
            "credencial": issue_agent_token(agent),
            "api_url": request.host_url.rstrip("/"),
        }), 201

    @safe_route
    def control(self, token_data, agent_id):
        forbidden = self._require_admin(token_data)
        if forbidden:
            return forbidden
        agent = db.session.get(TimoVoiceAgent, agent_id)
        if not agent or agent.usuario_id != token_data.get("id"):
            return jsonify("Agente do Timo não encontrado."), 404
        body = request.get_json(silent=True) or {}
        enabled = bool(body.get("habilitado"))
        preference = self._preference(agent.usuario_id)
        preference.habilitado = enabled
        preference.agente_preferido_id = agent.id
        db.session.commit()
        from utils.timo_voice_socket import emit_agent_control
        emit_agent_control(agent.id, enabled)
        return jsonify({"agente": self._serialize(agent, preference), "habilitado": enabled}), 200

    @safe_route
    def select(self, token_data, agent_id):
        forbidden = self._require_admin(token_data)
        if forbidden:
            return forbidden
        agent = db.session.get(TimoVoiceAgent, agent_id)
        if not agent or agent.usuario_id != token_data.get("id") or not agent.ativo:
            return jsonify("Agente do Timo não encontrado."), 404
        preference = self._preference(agent.usuario_id)
        preference.agente_preferido_id = agent.id
        db.session.commit()
        return jsonify({"agente": self._serialize(agent, preference)}), 200

    @safe_route
    def revoke(self, token_data, agent_id):
        forbidden = self._require_admin(token_data)
        if forbidden:
            return forbidden
        agent = db.session.get(TimoVoiceAgent, agent_id)
        if not agent or agent.usuario_id != token_data.get("id"):
            return jsonify("Agente do Timo não encontrado."), 404
        agent.ativo = False
        agent.token_version += 1
        preference = self._preference(agent.usuario_id)
        if preference.agente_preferido_id == agent.id:
            preference.agente_preferido_id = None
            preference.habilitado = False
        db.session.commit()
        from utils.timo_voice_socket import disconnect_agent
        disconnect_agent(agent.id)
        return jsonify({"message": "Agente desvinculado."}), 200
