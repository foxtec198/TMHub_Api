# Recursos do assistente Timo: extração de entidades.
# Biblioteca padrão.
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import unicodedata
# Dependências externas.
from dateutil.relativedelta import relativedelta

def normalize_text(text: str):
    return "".join(c for c in unicodedata.normalize("NFD", text.lower().strip()) if not unicodedata.combining(c))

def extract_period(text: str):
    month_options = ["esse mes", "este mes", "mes atual", "deste mes", "desse mes", "neste mes", "nesse mes"]
    
    text = normalize_text(text)
    today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

    if re.search(r"\b(?:(?:essa|esta|nessa|nesta|dessa|desta) semana|semana atual)\b", text):
        start = today - timedelta(days=today.weekday())
        return {"type": "week", "start": start.isoformat(),
                "end": (start + timedelta(days=6)).isoformat(), "label": "nesta semana"}

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
    if ( "mes passado" in text or "mês passado" in text ):
        previous_month = today - relativedelta(months=1)
        start = previous_month.replace(day=1)
        end = start + relativedelta(months=1) - timedelta(days=1)

        return {
            "type": "month",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "label": "no mês passado"
        }

    # MÊS ATUAL
    if any(value in text for value in month_options):
        start = today.replace(day=1)

        end = start + relativedelta(months=1) - timedelta(days=1)

        return {
            "type": "month",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "label": "este mês"
        }

    # Se não informou período, podemos assumir hoje.
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
        "postos_descobertos", "vagas_concluidas_periodo", "resumo_admissoes",
    }

    if intent in intents_with_period: entities["period"] = extract_period(text)
    return entities
