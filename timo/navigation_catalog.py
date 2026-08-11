"""Catálogo único das telas que o Timo pode abrir por comando de voz.

Manter as frases de treinamento no mesmo lugar da rota evita que uma tela
apareça na configuração sem que o classificador consiga reconhecê-la.
"""

import re
import unicodedata


def _screen(label, path, permission=None, *, admin_only=False, commands=()):
    return {
        "label": label,
        "path": path,
        "permission": permission,
        "admin_only": admin_only,
        "commands": list(commands),
    }


NAVIGATION_SCREENS = {
    "navegar_inicio": _screen(
        "Início e suporte", "/init", commands=(
            "abrir inicio", "voltar ao inicio", "ir para inicio", "abrir painel inicial", "abrir suporte",
        ),
    ),
    "navegar_projetos": _screen(
        "Meus Projetos", "/projetos", "projetos", commands=(
            "abrir meus projetos", "abre meus projetos", "ir para projetos", "me leve para projetos", "mostrar projetos",
        ),
    ),
    "navegar_configuracoes": _screen(
        "Configurações", "/configuracoes", commands=(
            "abrir configuracoes", "abre configuracoes", "ir para configuracoes", "me leve para configuracoes", "abrir minha conta",
        ),
    ),
    "navegar_faltas": _screen(
        "Controle de Faltas", "/controle-faltas", "controle_faltas", commands=(
            "abrir controle de faltas", "abre o controle de faltas", "abra o controle de faltas", "ir para faltas", "mostrar controle de faltas",
        ),
    ),
    "navegar_glosas": _screen(
        "Controle de Glosas", "/controle-glosas", "controle_glosas", commands=(
            "abrir controle de glosas", "abre as glosas", "ir para glosas", "me leve para controle de glosas", "mostrar glosas",
        ),
    ),
    "navegar_dashboard_reposicoes": _screen(
        "Dashboard de Reposições", "/reports/reposicoes", "dashboard_reposicoes", commands=(
            "abrir dashboard de reposicoes", "abrir painel de reposicoes", "ir para dashboard reposicoes", "mostrar dashboard de coberturas", "abrir relatorio de reposicoes",
        ),
    ),
    "navegar_colaboradores": _screen(
        "Colaboradores por departamento", "/reports/colaboradores-departamento", "dashboard_colaboradores", commands=(
            "abrir colaboradores por departamento", "abre os colaboradores", "ir para colaboradores", "mostrar colaboradores por departamento", "abrir lista de colaboradores",
        ),
    ),
    "navegar_ponto48": _screen(
        "Ponto 48 horas", "/reports/ponto-48-horas", "dashboard_ponto48", commands=(
            "abrir ponto 48 horas", "abrir ponto 48", "ir para ponto 48", "mostrar painel ponto 48", "abrir dashboard ponto 48",
        ),
    ),
    "navegar_dashboard_admissoes": _screen(
        "Dashboard de Admissões", "/reports/admissoes", "dashboard_admissoes", commands=(
            "abrir dashboard de admissoes", "mostrar dashboard admissoes", "ir para relatorio de admissoes", "abrir painel de admissoes", "ver dashboard vagas",
        ),
    ),
    "navegar_dashboard_faltas": _screen(
        "Dashboard de Faltas", "/reports/faltas", "dashboard_faltas", commands=(
            "abrir dashboard de faltas", "mostrar dashboard faltas", "ir para relatorio de faltas", "abrir painel de faltas", "ver indicadores de faltas",
        ),
    ),
    "navegar_dashboard_logistica": _screen(
        "Dashboard de Logística", "/reports/logistica", "dashboard_logistica", commands=(
            "abrir dashboard de logistica", "mostrar dashboard logistica", "ir para relatorio de estoque", "abrir painel de produtos", "ver indicadores de estoque",
        ),
    ),
    "navegar_dashboard_rescisoes": _screen(
        "Dashboard de Rescisões", "/reports/rescisoes", "dashboard_rescisoes", commands=(
            "abrir dashboard de rescisoes", "mostrar dashboard rescisoes", "ir para relatorio de rescisoes", "abrir painel de desligamentos", "ver indicadores de rescisoes",
        ),
    ),
    "navegar_dashboard_projetos": _screen(
        "Dashboard de Projetos", "/reports/projetos", "dashboard_projetos", commands=(
            "abrir dashboard de projetos", "mostrar dashboard projetos", "ir para relatorio de projetos", "abrir painel de projetos", "ver indicadores de projetos",
        ),
    ),
    "navegar_dashboard_glosas": _screen(
        "Dashboard de Glosas", "/reports/glosas", "dashboard_glosas", commands=(
            "abrir dashboard de glosas", "mostrar dashboard glosas", "ir para relatorio de glosas", "abrir painel de glosas", "ver indicadores de glosas",
        ),
    ),
    "navegar_rocada": _screen(
        "Dashboard de Roçada", "/reports/rocada", "dashboard_glosas", commands=(
            "abrir roçada", "abrir rocada", "mostrar dashboard de rocada", "ir para controle de rocada", "ver painel de roçada",
        ),
    ),
    "navegar_dashboard_pcd": _screen(
        "Dashboard PCD", "/reports/pcd", "dashboard_pcd", commands=(
            "abrir dashboard pcd", "mostrar dashboard pcd", "ir para relatorio pcd", "abrir painel pcd", "ver indicadores pcd",
        ),
    ),
    "navegar_indicador_pcd": _screen(
        "Indicador PCD", "/indicadores/pcd", "indicador_pcd", commands=(
            "abrir indicador pcd", "abrir controle pcd", "ir para indicador pcd", "mostrar pcd", "abrir cadastro pcd",
        ),
    ),
    "navegar_vagas": _screen(
        "Vagas de substituição", "/admissao/vagas", "admissoes", commands=(
            "abrir vagas", "abrir vagas de substituicao", "ir para admissoes", "mostrar vagas abertas", "abrir controle de vagas",
        ),
    ),
    "navegar_aditivos": _screen(
        "Vagas de aditivos", "/admissao/aditivos", "admissoes", commands=(
            "abrir vagas de aditivos", "abrir aditivos", "ir para aditivos", "mostrar vagas aditivas", "abrir admissao de aditivos",
        ),
    ),
    "navegar_requisicoes": _screen(
        "Requisições", "/reposicoes/requisicoes", "reposicoes", commands=(
            "abrir requisicoes", "abrir reposicoes", "ir para requisicoes", "mostrar solicitacoes de reposicao", "abrir painel de requisicoes",
        ),
    ),
    "navegar_reservas": _screen(
        "Reservas técnicas", "/reposicoes/reservas", "reservas", commands=(
            "abrir reservas", "abrir reservas tecnicas", "ir para reservas", "mostrar reservas", "abrir painel de reservas",
        ),
    ),
    "navegar_historico_reposicoes": _screen(
        "Histórico de Reposições", "/reposicoes/historico", "historico_reposicoes", commands=(
            "abrir historico de reposicoes", "abrir historico", "ir para historico de coberturas", "mostrar historico de requisicoes", "ver historico reposicoes",
        ),
    ),
    "navegar_produtos": _screen(
        "Produtos", "/estoque/produtos", "estoque_produtos", commands=(
            "abrir produtos", "abrir estoque", "ir para produtos", "mostrar produtos em estoque", "abrir cadastro de produtos",
        ),
    ),
    "navegar_codigos_barras": _screen(
        "Códigos de barras", "/estoque/codigos-de-barras", "estoque_codigos", commands=(
            "abrir codigos de barras", "abrir codigo de barras", "ir para codigos de barras", "mostrar gerador de codigo", "gerar codigo de barras",
        ),
    ),
    "navegar_movimentacoes": _screen(
        "Movimentações de estoque", "/estoque/movimentacoes", "estoque_movimentos", commands=(
            "abrir movimentacoes", "abrir movimentacoes de estoque", "ir para movimentacoes", "mostrar entradas e saidas", "abrir historico de estoque",
        ),
    ),
    "navegar_medidas_disciplinares": _screen(
        "Medidas Disciplinares", "/controle-medidas-disciplinares", "controle_medidas_disciplinares", commands=(
            "abrir medidas disciplinares", "abrir controle disciplinar", "ir para medidas disciplinares", "mostrar medidas", "abrir advertencias",
        ),
    ),
    "navegar_rescisoes": _screen(
        "Controle de Rescisões", "/rescisoes", "controle_rescisoes", commands=(
            "abrir rescisoes", "abrir controle de rescisoes", "ir para desligamentos", "mostrar rescisoes", "abrir controle de desligamentos",
        ),
    ),
    "navegar_estrutura": _screen(
        "Estrutura", "/estrutura", "estrutura", commands=(
            "abrir estrutura", "abrir centros de custo", "ir para estrutura", "mostrar estrutura", "abrir locais e ativos",
        ),
    ),
    "navegar_rotinas": _screen(
        "Rotinas", "/tm-ops/gestao", "tm_ops", admin_only=True, commands=(
            "abrir rotinas", "abrir gestao de rotinas", "ir para rotinas", "mostrar scheduler", "abrir tm ops rotinas",
        ),
    ),
    "navegar_checklists": _screen(
        "Checklists", "/tm-ops/checklists", "tm_ops", admin_only=True, commands=(
            "abrir checklists", "abrir checklist", "ir para checklists", "mostrar checklists", "abrir tm ops checklists",
        ),
    ),
    "navegar_tarefas": _screen(
        "Tarefas administrativas", "/tm-ops/tarefas", "tm_ops", admin_only=True, commands=(
            "abrir tarefas", "abrir tarefas administrativas", "ir para tarefas", "mostrar tarefas do scheduler", "abrir tm ops tarefas",
        ),
    ),
}


NAVIGATION_ACTION_PATHS = {
    definition["path"]: {
        "label": definition["label"],
        "permission": definition["permission"],
        "admin_only": definition["admin_only"],
    }
    for definition in NAVIGATION_SCREENS.values()
}


NAVIGATION_INTENTS = {
    intent: {
        "label": definition["label"],
        "description": f"Abre a tela {definition['label']}.",
        "response": f"Abrindo {definition['label']}.",
        "action_type": "navigate",
        "action_value": definition["path"],
    }
    for intent, definition in NAVIGATION_SCREENS.items()
}


NAVIGATION_TRAINING_EXAMPLES = [
    {"text": command, "intent": intent}
    for intent, definition in NAVIGATION_SCREENS.items()
    for command in definition["commands"]
]


def _normalize_command(value):
    normalized = unicodedata.normalize("NFD", str(value or "").strip().lower())
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", normalized)


NAVIGATION_COMMANDS = {
    _normalize_command(command): intent
    for intent, definition in NAVIGATION_SCREENS.items()
    for command in definition["commands"]
}


def navigation_intent_for_command(command):
    """Resolve frases oficiais sem depender da confiança estatística do modelo."""
    return NAVIGATION_COMMANDS.get(_normalize_command(command))
