import re

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


def normalize_text(text: str):
    return (
        text
        .lower()
        .strip()
    )


def extract_period(text: str):
    text = normalize_text(text)

    today = datetime.now().date()

    # HOJE
    if re.search(r"\bhoje\b", text):
        return {
            "type": "day",
            "start": today.isoformat(),
            "end": today.isoformat(),
            "label": "hoje"
        }

    # ONTEM
    if re.search(r"\bontem\b", text):
        yesterday = today - timedelta(days=1)

        return {
            "type": "day",
            "start": yesterday.isoformat(),
            "end": yesterday.isoformat(),
            "label": "ontem"
        }

    # MÊS PASSADO
    if (
        "mes passado" in text
        or "mês passado" in text
    ):
        previous_month = today - relativedelta(months=1)

        start = previous_month.replace(day=1)

        end = (
            start
            + relativedelta(months=1)
            - timedelta(days=1)
        )

        return {
            "type": "month",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "label": "no mês passado"
        }

    # MÊS ATUAL
    if any(value in text for value in [
        "esse mes",
        "esse mês",
        "este mes",
        "este mês",
        "mes atual",
        "mês atual"
    ]):
        start = today.replace(day=1)

        end = (
            start
            + relativedelta(months=1)
            - timedelta(days=1)
        )

        return {
            "type": "month",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "label": "este mês"
        }

    # Se não informou período,
    # podemos assumir hoje.
    return {
        "type": "day",
        "start": today.isoformat(),
        "end": today.isoformat(),
        "label": "hoje"
    }


def extract_entities(text: str, intent: str):
    entities = {}

    intents_with_period = {
        "faltas_periodo",
        "reposicoes_periodo",
        "postos_descobertos"
    }

    if intent in intents_with_period:
        entities["period"] = extract_period(text)

    return entities