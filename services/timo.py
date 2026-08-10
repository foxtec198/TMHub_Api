import re
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import jsonify, request
from sqlalchemy import extract

from models.controle_faltas import AbsenceControl
from utils.filial_scope import apply_cost_center_scope
from utils.permissions import has_permission
from utils.safe_route import safe_route


SAO_PAULO = ZoneInfo("America/Sao_Paulo")


class TimoCommandService:
    """Interpreta comandos curtos e devolve somente dados textuais/estruturados."""

    NAVIGATION_COMMANDS = (
        (("faltas", "falta"), "/controle-faltas", "Abrindo o Controle de Faltas."),
        (("reposicoes", "reposicao", "requisicoes", "requisicao", "solicitacoes", "solicitacao"), "/reposicoes/requisicoes", "Abrindo Requisições."),
        (("reservas", "reserva"), "/reposicoes/reservas", "Abrindo Reservas."),
        (("projetos", "projeto"), "/projetos", "Abrindo Meus Projetos."),
        (("estoque", "produtos", "produto"), "/estoque/produtos", "Abrindo Produtos em estoque."),
    )

    @staticmethod
    def _normalize(value):
        text = unicodedata.normalize("NFD", str(value or "").strip().lower())
        text = "".join(character for character in text if not unicodedata.combining(character))
        return re.sub(r"\s+", " ", text)

    @safe_route
    def process(self, token_data):
        body = request.get_json(silent=True) or {}
        command = self._normalize(body.get("command"))
        if not command:
            return jsonify({"success": False, "message": "Não entendi o comando."}), 400
        if len(command) > 500:
            return jsonify({"success": False, "message": "Esse comando é muito longo."}), 400

        if "falta" in command and any(term in command for term in ("mes", "quantas", "total")):
            if not (
                has_permission(token_data, "dashboard_faltas", "view")
                or has_permission(token_data, "controle_faltas", "view")
            ):
                return jsonify({
                    "success": False,
                    "message": "Você não possui acesso aos dados de faltas.",
                    "action": None,
                }), 403
            today = datetime.now(SAO_PAULO)
            query = AbsenceControl.query.filter(
                extract("year", AbsenceControl.data_falta) == today.year,
                extract("month", AbsenceControl.data_falta) == today.month,
            )
            total = apply_cost_center_scope(
                query, AbsenceControl.centro_custo_id, token_data
            ).count()
            return jsonify({
                "success": True,
                "message": f"Tivemos {total} falta{'s' if total != 1 else ''} neste mês.",
                "action": None,
            }), 200

        for aliases, path, message in self.NAVIGATION_COMMANDS:
            if any(alias in command for alias in aliases):
                return jsonify({
                    "success": True,
                    "message": message,
                    "action": {"type": "navigate", "path": path},
                }), 200

        return jsonify({
            "success": False,
            "message": "Ainda não reconheci esse comando. Tente, por exemplo: Faltas, Requisições, Reservas, Projetos ou Estoque.",
            "action": None,
        }), 200
