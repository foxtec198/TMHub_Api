# Recursos do assistente Timo: catálogo analítico.
"""Intenções analíticas operacionais do Timo.

As consultas ficam declaradas aqui para que o catálogo exibido aos admins e
as frases usadas pelo classificador sempre evoluam juntos.
"""

# Biblioteca padrão.
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
        "Situação atual das RTs no escopo selecionado: {disponiveis} disponível(is), {faltas} marcada(s) como FALTA e {apoio} em APOIO. Total: {total_reservas}; indisponíveis: {indisponiveis}.{outras_label}",
        (
            "quantas reservas estao disponiveis", "quantas reservas estão disponíveis", "reservas disponiveis",
            "reservas disponíveis", "tem reserva disponivel", "tem reserva disponível",
            "quantos volantes temos", "quantos reservas tecnicas temos",
            "quantas rts disponiveis", "quantas rts estao disponiveis", "rts disponiveis",
            "quantos rts disponiveis", "quantos rts estao disponiveis", "tem rt disponivel",
            "resumo das reservas", "resumo das rts", "quantas reservas faltaram",
            "quantas rts faltaram", "quantas reservas estao de apoio", "quantas rts estao de apoio",
            "quantas reservas estao indisponiveis", "quantas reservas em apoio", "quantas rts em apoio",
        ),
        ("{total}", "{disponiveis}", "{faltas}", "{apoio}", "{total_reservas}", "{indisponiveis}", "{outras_label}"),
    ),
    "pcds_cadastrados": _query(
        "Colaboradores PCD no cadastro",
        "Conta os colaboradores marcados como PCD no cadastro atual, no escopo permitido, incluindo todas as situações.",
        "Há {total} colaborador(es) marcado(s) como PCD no cadastro atual, no escopo selecionado (todas as situações).",
        (
            "quantos pcds possuimos", "quantos pcds possuimos hoje", "quantos pcds temos",
            "quantos pcds temos hoje", "quantos pcd temos", "total de pcds",
            "quantos colaboradores pcd temos", "quantas pessoas com deficiencia temos",
        ),
        ("{total}",),
    ),
    "vagas_concluidas_periodo": _query(
        "Vagas concluídas no período",
        "Conta vagas com status Concluído pela data de conclusão, incluindo substituições e aditivos.",
        "{period_label}: {concluidas} vaga(s) concluída(s), pela data de conclusão (substituições e aditivos).",
        tuple(f"{phrase} {period}" for phrase in (
            "quantas vagas foram concluidas", "quantas vagas foram completas", "quantas vagas completas",
            "quantas vagas concluidas", "total de vagas completas", "total de vagas concluidas",
            "quantas vagas completamos", "quantas vagas concluimos",
        ) for period in ("hoje", "ontem", "essa semana", "esta semana", "esse mes", "este mes", "mes passado")),
        ("{concluidas}", "{period_label}"),
    ),
    "resumo_admissoes": _query(
        "Resumo de admissões",
        "Resume cadastros, conclusões e inícios registrados no período, mais o andamento atual das vagas.",
        "{period_label}: {cadastradas} vaga(s) cadastrada(s), {concluidas} concluída(s) e {inicios} início(s) de trabalho informado(s) para o período. Atualmente: {em_andamento} em andamento — {abertas} em Aberta, {entrevista} em Entrevista, {certidao} em Certidão, {aso} em ASO e {unico} em Único. Inclui substituições e aditivos.",
        tuple(f"{phrase} {period}".strip() for phrase in (
            "resumo de admissoes", "resumo das admissoes", "como estao as admissoes", "resumo de vagas",
        ) for period in ("", "hoje", "ontem", "essa semana", "esse mes", "este mes", "mes passado")),
        ("{period_label}", "{cadastradas}", "{concluidas}", "{inicios}", "{em_andamento}", "{abertas}", "{entrevista}", "{certidao}", "{aso}", "{unico}"),
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
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


ANALYTICS_COMMANDS = {
    _normalize_command(command): intent
    for intent, definition in ANALYTICS_INTENTS.items()
    for command in definition["commands"]
}


def analytics_intent_for_command(command):
    """Resolve frases analíticas oficiais antes do fallback estatístico."""
    normalized = _normalize_command(command)
    exact = ANALYTICS_COMMANDS.get(normalized)
    if exact:
        return exact
    # Variações de consulta sem transformar pedidos de ajuda/navegação em contagens.
    if re.match(r"^(?:quant\w*|total|resumo|como estao)\b", normalized):
        if re.search(r"\bvagas?\b", normalized) and re.search(r"\b(?:complet\w*|conclu\w*)\b", normalized):
            return "vagas_concluidas_periodo"
        if "admisso" in normalized or ("resumo" in normalized and "vagas" in normalized):
            return "resumo_admissoes"
        if re.search(r"\b(?:rts?|reservas?)\b", normalized) and re.search(r"disponiv|apoio|falt\w*|resumo", normalized):
            return "reservas_disponiveis"
        if "vagas" in normalized and re.search(r"\babert\w*\b", normalized):
            return "vagas_abertas"
    return None
