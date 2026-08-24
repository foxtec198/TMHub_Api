"""Serviço de telemetria de uso e cálculo diário de Edinhos."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from flask import jsonify, request
from sqlalchemy import func

from models.uso_tmhub import TMHubEdinhoLedger, TMHubUsageDaily, TMHubUsageEvent
from models.usuarios import Users
from utils.db import db
from utils.filial_scope import is_admin
from utils.safe_route import safe_route
from utils.socket import socketio


SAO_PAULO = ZoneInfo("America/Sao_Paulo")
EVENT_PAGE_VIEW = "pagina_visitada"
EVENT_ACTION = "acao_concluida"
VALID_CLIENT_EVENTS = {"pagina_visitada", "atividade"}
MAX_HEARTBEAT_SECONDS = 90
EDINHO_SECONDS = 15 * 60
EDINHO_DAILY_CAP = 20
EDINHO_ACTION_CAP = 8


def _now():
    return datetime.now(SAO_PAULO)


def _safe_route(value):
    route = str(value or "").strip()
    if not route.startswith("/"):
        return "/"
    return route[:240]


def _parse_day(value):
    if not value:
        return _now().date()
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


class TMHubUsageService:
    """Armazena somente atividade agregada e eventos auditáveis de alto nível."""

    @staticmethod
    def _edinhos_for(daily):
        # Regra inicial: 1 Edinho a cada 15 min ativos + ações úteis, limitada
        # por dia para não incentivar apenas volume de cliques.
        by_time = int(daily.segundos_ativos or 0) // EDINHO_SECONDS
        by_actions = min(int(daily.acoes_concluidas or 0), EDINHO_ACTION_CAP)
        return min(EDINHO_DAILY_CAP, by_time + by_actions)

    @classmethod
    def _daily(cls, user_id, occurred_at):
        current_day = occurred_at.date()
        daily = TMHubUsageDaily.query.filter_by(
            usuario_id=user_id,
            dia=current_day,
        ).first()
        if daily:
            return daily

        daily = TMHubUsageDaily(
            usuario_id=user_id,
            dia=current_day,
            primeira_atividade_em=occurred_at,
            ultima_atividade_em=occurred_at,
        )
        db.session.add(daily)
        db.session.flush()
        return daily

    @classmethod
    def _sync_edinho_ledger(cls, daily):
        ledger = TMHubEdinhoLedger.query.filter_by(uso_diario_id=daily.id).first()
        if not ledger:
            ledger = TMHubEdinhoLedger(
                usuario_id=daily.usuario_id,
                uso_diario_id=daily.id,
                tipo="uso_diario",
                descricao=f"Atividade no TMHub em {daily.dia.strftime('%d/%m/%Y')}",
            )
            db.session.add(ledger)
        ledger.quantidade = int(daily.edinhos_gerados or 0)

    @classmethod
    def record(
        cls,
        user_id,
        event_type,
        route=None,
        method=None,
        active_seconds=0,
        occurred_at=None,
    ):
        """Registra uma atividade de forma resiliente e sem afetar a operação."""
        if not user_id:
            return None

        now = occurred_at or _now()
        daily = cls._daily(int(user_id), now)
        daily.ultima_atividade_em = now
        daily.primeira_atividade_em = min(daily.primeira_atividade_em or now, now)

        if event_type == EVENT_PAGE_VIEW:
            daily.paginas_visitadas = int(daily.paginas_visitadas or 0) + 1
        elif event_type == EVENT_ACTION:
            daily.acoes_concluidas = int(daily.acoes_concluidas or 0) + 1

        safe_seconds = max(0, min(int(active_seconds or 0), MAX_HEARTBEAT_SECONDS))
        if safe_seconds:
            daily.segundos_ativos = int(daily.segundos_ativos or 0) + safe_seconds

        daily.edinhos_gerados = cls._edinhos_for(daily)
        cls._sync_edinho_ledger(daily)

        if event_type in {EVENT_PAGE_VIEW, EVENT_ACTION}:
            db.session.add(TMHubUsageEvent(
                uso_diario_id=daily.id,
                usuario_id=daily.usuario_id,
                tipo=event_type,
                rota=_safe_route(route),
                metodo=str(method or "").upper()[:12] or None,
                ocorrido_em=now,
            ))

        db.session.commit()
        socketio.emit("uso_tmhub_update", {"dia": daily.dia.isoformat()})
        return daily

    @classmethod
    def record_successful_mutation(cls, token_data, route, method):
        """Hook global: ações já concluídas também entram no resumo do dia."""
        if not token_data or _safe_route(route).startswith("/uso"):
            return
        try:
            cls.record(token_data.get("id"), EVENT_ACTION, route=route, method=method)
        except Exception:
            db.session.rollback()

    @staticmethod
    def _serialize_daily(daily, user, include_events=False):
        result = {
            "id": daily.id,
            "dia": daily.dia.isoformat(),
            "usuario": {
                "id": user.id,
                "nome": user.nome,
                "foto_perfil": user.foto_perfil,
            },
            "primeira_atividade_em": daily.primeira_atividade_em.isoformat() if daily.primeira_atividade_em else None,
            "ultima_atividade_em": daily.ultima_atividade_em.isoformat() if daily.ultima_atividade_em else None,
            "segundos_ativos": int(daily.segundos_ativos or 0),
            "paginas_visitadas": int(daily.paginas_visitadas or 0),
            "acoes_concluidas": int(daily.acoes_concluidas or 0),
            "edinhos_gerados": int(daily.edinhos_gerados or 0),
        }
        if include_events:
            result["timeline"] = [{
                "id": event.id,
                "tipo": event.tipo,
                "rota": event.rota,
                "metodo": event.metodo,
                "ocorrido_em": event.ocorrido_em.isoformat() if event.ocorrido_em else None,
            } for event in daily.eventos.order_by(TMHubUsageEvent.ocorrido_em.asc()).all()]
        return result

    @staticmethod
    def _edinho_balance(user_id):
        return int(
            db.session.query(func.coalesce(func.sum(TMHubEdinhoLedger.quantidade), 0))
            .filter(TMHubEdinhoLedger.usuario_id == user_id)
            .scalar() or 0
        )

    @safe_route
    def activity(self, token_data):
        body = request.get_json(silent=True) or {}
        event_type = str(body.get("tipo") or "atividade").strip().lower()
        if event_type not in VALID_CLIENT_EVENTS:
            return jsonify("Tipo de atividade inválido."), 400

        try:
            active_seconds = int(body.get("segundos_ativos") or 0)
        except (TypeError, ValueError):
            return jsonify("Tempo de atividade inválido."), 400

        try:
            daily = self.record(
                token_data.get("id"),
                event_type,
                route=body.get("rota"),
                active_seconds=active_seconds,
            )
        except Exception:
            db.session.rollback()
            return jsonify("Não foi possível registrar sua atividade."), 500
        return jsonify({
            "dia": daily.dia.isoformat(),
            "edinhos_gerados": daily.edinhos_gerados,
        }), 200

    @safe_route
    def read(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem consultar o controle de uso."), 403

        selected_day = _parse_day(request.args.get("dia"))
        if not selected_day:
            return jsonify("Informe uma data válida no formato AAAA-MM-DD."), 400

        rows = (
            db.session.query(TMHubUsageDaily, Users)
            .join(Users, Users.id == TMHubUsageDaily.usuario_id)
            .filter(TMHubUsageDaily.dia == selected_day)
            .order_by(TMHubUsageDaily.segundos_ativos.desc(), TMHubUsageDaily.acoes_concluidas.desc(), Users.nome)
            .all()
        )
        records = [self._serialize_daily(daily, user, include_events=True) for daily, user in rows]
        totals = {
            "usuarios_ativos": len(records),
            "segundos_ativos": sum(item["segundos_ativos"] for item in records),
            "paginas_visitadas": sum(item["paginas_visitadas"] for item in records),
            "acoes_concluidas": sum(item["acoes_concluidas"] for item in records),
            "edinhos_gerados": sum(item["edinhos_gerados"] for item in records),
        }
        return jsonify({"dia": selected_day.isoformat(), "resumo": totals, "registros": records}), 200

    @safe_route
    def my_day(self, token_data):
        selected_day = _parse_day(request.args.get("dia"))
        if not selected_day:
            return jsonify("Informe uma data válida no formato AAAA-MM-DD."), 400
        daily = TMHubUsageDaily.query.filter_by(usuario_id=token_data.get("id"), dia=selected_day).first()
        user = db.session.get(Users, token_data.get("id"))
        if not daily or not user:
            return jsonify({"dia": selected_day.isoformat(), "edinhos_gerados": 0, "saldo_edinhos": 0, "timeline": []}), 200
        payload = self._serialize_daily(daily, user, include_events=True)
        payload["saldo_edinhos"] = self._edinho_balance(user.id)
        return jsonify(payload), 200
