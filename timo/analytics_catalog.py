"""Intenções analíticas operacionais do Timo.

As consultas ficam declaradas aqui para que o catálogo exibido aos admins e
as frases usadas pelo classificador sempre evoluam juntos.
"""

import re
import unicodedata


def _query(label, description, response, commands, variables):
    return {
        "label": label,
        "description": description,
        "response": response,
        "action_type": "none",
        "action_value": None,
        "commands": list(commands),
        "variables": list(variables),
    }


ANALYTICS_INTENTS = {
    "absenteismo_periodo": _query(
        "Absenteísmo operacional",
        "Calcula a média de faltas e o percentual sobre o quadro ativo no período solicitado.",
        "{period_label}: média de {media_faltas_dia} falta(s) por dia, ou {percentual_absenteismo}% do quadro ativo de {quadro_ativo} pessoa(s).",
        (
            "qual o absenteismo hoje", "qual o absenteísmo hoje", "como esta o absenteismo hoje",
            "taxa de absenteismo hoje", "indice de absenteismo", "índice de absenteísmo",
            "absenteismo do mes", "absenteísmo deste mês",
        ),
        ("{period_label}", "{media_faltas_dia}", "{percentual_absenteismo}", "{quadro_ativo}", "{faltas}"),
    ),
    "coberturas_periodo": _query(
        "Coberturas e postos descobertos",
        "Mostra decisões de cobertura, postos sem cobertura e requisições ainda abertas.",
        "{period_label}: {cobertas} cobertura(s), {descobertas} posto(s) descoberto(s), {abertas} requisição(ões) em aberto e {taxa_cobertura}% de cobertura nas decisões.",
        (
            "como estao as coberturas hoje", "como estão as coberturas hoje", "quantos postos foram cobertos hoje",
            "quantos postos estao descobertos hoje", "situação das coberturas", "situacao das reposicoes hoje",
            "analise de cobertura hoje", "análise de cobertura deste mês", "coberturas do mes",
        ),
        ("{period_label}", "{cobertas}", "{descobertas}", "{abertas}", "{taxa_cobertura}"),
    ),
    "faltas_pendentes": _query(
        "Faltas pendentes de tratativa",
        "Mostra quantas faltas aguardam tratativa e quantas já passaram do prazo documental.",
        "Há {pendentes} falta(s) pendente(s) de tratativa; {atrasadas} está(ão) com prazo documental vencido.",
        (
            "quantas faltas estao pendentes", "quantas faltas estão pendentes", "faltas pendentes",
            "faltas para tratar", "o que esta pendente nas faltas", "o que está pendente nas faltas",
            "atestados vencidos", "quantas faltas atrasadas",
        ),
        ("{pendentes}", "{atrasadas}"),
    ),
    "quadro_lotacao": _query(
        "Análise de quadro de lotação",
        "Compara a capacidade planejada dos centros com os colaboradores trabalhando no quadro atual.",
        "O QL tem {quadro_ativo} ativo(s) para {capacidade_planejada} posição(ões) planejada(s), em {centros_planejados} centro(s): déficit de {deficit}, excedente de {excedente} e {centros_sem_capacidade} sem capacidade definida.",
        (
            "como esta o quadro de lotacao", "como está o quadro de lotação", "analise de ql",
            "análise de ql", "quadro de lotacao atual", "quadro de lotação atual",
            "capacidade dos contratos", "como esta a lotacao",
        ),
        ("{quadro_ativo}", "{capacidade_planejada}", "{centros_planejados}", "{deficit}", "{excedente}", "{centros_sem_capacidade}"),
    ),
    "quadro_lotacao_critico": _query(
        "Contratos críticos no QL",
        "Aponta os contratos com maior déficit entre capacidade planejada e quadro trabalhando.",
        "{contratos_criticos}",
        (
            "quais contratos estao com deficit", "quais contratos estão com déficit", "contratos criticos de ql",
            "contratos críticos de ql", "onde falta colaborador", "quais locais estao descobertos no ql",
            "maiores deficits de lotacao", "maiores déficits de lotação",
        ),
        ("{contratos_criticos}", "{qtd_criticos}"),
    ),
    "reservas_disponiveis": _query(
        "Reservas técnicas disponíveis",
        "Mostra o total de reservas técnicas que podem ser utilizadas no escopo atual.",
        "Temos {total} reserva(s) técnica(s) disponível(is) no escopo atual.",
        (
            "quantas reservas estao disponiveis", "quantas reservas estão disponíveis", "reservas disponiveis",
            "reservas disponíveis", "tem reserva disponivel", "tem reserva disponível",
            "quantos volantes temos", "quantos reservas tecnicas temos",
        ),
        ("{total}"),
    ),
}


ANALYTICS_TRAINING_EXAMPLES = [
    {"text": command, "intent": intent}
    for intent, definition in ANALYTICS_INTENTS.items()
    for command in definition["commands"]
]


def _normalize_command(value):
    normalized = unicodedata.normalize("NFD", str(value or "").strip().lower())
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", normalized)


ANALYTICS_COMMANDS = {
    _normalize_command(command): intent
    for intent, definition in ANALYTICS_INTENTS.items()
    for command in definition["commands"]
}


def analytics_intent_for_command(command):
    """Resolve frases analíticas oficiais antes do fallback estatístico."""
    return ANALYTICS_COMMANDS.get(_normalize_command(command))
