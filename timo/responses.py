RESPONSES = {
    "faltas_periodo": (
        "{total} faltas {period_label}."
    ),

    "reposicoes_periodo": (
        "{total} reposições {period_label}."
    ),

    "postos_descobertos": (
        "{total} postos ficaram sem cobertura "
        "{period_label}."
    ),

    "vagas_abertas": (
        "Existem {total} vagas abertas."
    )
}


def build_response(intent, data):
    # Comandos que representam ação
    if data.get("action"):
        return None

    template = RESPONSES.get(intent)

    if not template:
        return None

    return template.format(**data)