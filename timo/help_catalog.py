"""Orientações baseadas nos formulários reais do TMHub, sem geração de ações."""
import re

from timo.command_catalog import normalize_command


def _guide(label, response, permission=None, action="view"):
    return {"label": label, "description": "Orientação de uso do TMHub.",
            "response": response, "permission": permission, "permission_action": action,
            "action_type": "none", "action_value": None}


HELP_INTENTS = {
    "ajuda_chamados": _guide("Como abrir um chamado",
        "Para abrir um chamado: 1. Acesse Chamados. 2. Clique em Novo chamado. "
        "3. Preencha Título e Descrição; o Motivo é opcional. 4. Clique em Abrir chamado. "
        "Depois acompanhe o atendimento na própria tela. Se quiser ir até lá, diga 'abrir chamados'.",
        "tickets", "create"),
    "ajuda_requisicoes": _guide("Como fazer uma requisição",
        "Para fazer uma requisição: 1. Acesse Requisições e escolha Lançamento rápido. "
        "2. Selecione o supervisor, quando esse campo estiver disponível, o colaborador ausente "
        "e o centro de custo. 3. Selecione a reserva ou marque Sem cobertura. "
        "4. Informe o motivo e a data da ausência; para falta injustificada, informe a advertência. "
        "5. Revise e clique em Criar requisição. Para ir à tela, diga 'abrir requisições'.",
        "reposicoes", "create"),
    "ajuda_reservas": _guide("Como consultar as reservas",
        "Em Reservas técnicas, consulte quem está disponível e quem está indisponível por FALTA ou APOIO. "
        "Para alterar a disponibilidade, use a ação da reserva; ao marcar Falta, informe o motivo exigido. "
        "O lançamento de falta também exige permissão no Controle de Faltas. "
        "Você pode me pedir 'resumo das RTs' ou 'abrir reservas'.", "reservas"),
    "ajuda_vagas": _guide("Como acompanhar vagas e admissões",
        "Em Vagas, acompanhe as colunas Aberta, Entrevista, Certidão, ASO, Único e Concluído. "
        "Ao mudar o status, preencha os campos solicitados; a conclusão exige identificação do contratado, "
        "jornada e data de início. Vagas de substituição e aditivos têm telas próprias. "
        "Você pode pedir 'resumo de admissões este mês', 'abrir vagas' ou 'abrir aditivos'.", "admissoes"),
    "ajuda_timo": _guide("O que o TIMO pode fazer",
        "Posso conversar, consultar faltas, RTs, PCDs, vagas e resumir admissões. "
        "Para vagas concluídas e admissões, use hoje, ontem, essa semana, esse mês ou mês passado. "
        "Também explico como abrir chamados e fazer requisições. Para navegar, diga 'abrir' e o nome da tela."),
}


def help_intent_for_command(command):
    text = normalize_command(command)
    if text in {"ajuda", "o que voce pode fazer", "como usar o timo", "como usar o sistema", "o que voce faz"}:
        return "ajuda_timo"
    if not re.search(r"\b(como|ajuda|ajude|ensina|ensine|explica|explique|instrucoes|passo a passo)\b", text):
        return None
    # 'Como estão as vagas?' é consulta, não tutorial.
    if re.search(r"\bcomo (?:esta|estao|anda|andam)\b", text):
        return None
    for pattern, intent in (
        (r"\b(?:chamados?|tickets?)\b", "ajuda_chamados"),
        (r"\b(?:requisic\w*|reposic\w*)\b", "ajuda_requisicoes"),
        (r"\b(?:reservas?|rts?)\b", "ajuda_reservas"),
        (r"\b(?:vagas?|admissoes|admissao)\b", "ajuda_vagas"),
    ):
        if re.search(pattern, text):
            return intent
    return None
