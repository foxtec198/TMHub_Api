# Recursos do assistente Timo: catálogo de comandos.
"""Resolução determinística das frases conhecidas do Timo.

O classificador é útil para variações novas, mas sua probabilidade entre muitas
intenções não é uma medida boa para frases que já constam no catálogo. Este
módulo resolve primeiro as frases oficiais e as frases históricas do CSV.
"""

# Biblioteca padrão.
from difflib import SequenceMatcher
from pathlib import Path
import csv
import re
import unicodedata

# Módulos internos da aplicação.
from timo.analytics_catalog import ANALYTICS_COMMANDS
from timo.navigation_catalog import NAVIGATION_COMMANDS


DATASET_PATH = Path(__file__).resolve().parent / "data" / "intents.csv"
FUZZY_MATCH_THRESHOLD = 0.82
STOP_WORDS = {
    "a", "as", "ao", "aos", "da", "das", "de", "do", "dos", "e",
    "em", "na", "nas", "no", "nos", "o", "os", "para", "por", "um",
    "uma", "me", "pra",
}


def normalize_command(value):
    normalized = unicodedata.normalize("NFD", str(value or "").strip().lower())
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _dataset_commands():
    commands = {}
    with DATASET_PATH.open("r", encoding="utf-8-sig", newline="") as dataset:
        for row in csv.DictReader(dataset):
            phrase = normalize_command(row.get("text"))
            intent = str(row.get("intent") or "").strip()
            if phrase and intent:
                commands[phrase] = intent
    return commands


KNOWN_COMMANDS = {
    **_dataset_commands(),
    **NAVIGATION_COMMANDS,
    **ANALYTICS_COMMANDS,
}


def _important_tokens(value):
    return {
        token
        for token in normalize_command(value).split()
        if token not in STOP_WORDS
    }


def known_intent_for_command(command):
    """Retorna uma intenção conhecida, primeiro exata e depois muito próxima.

    O limiar alto evita que frases sem relação sejam classificadas apenas por
    coincidência de palavras. A confiança retornada é de catálogo, não a
    probabilidade estatística do modelo.
    """
    normalized = normalize_command(command)
    if not normalized:
        return None

    exact = KNOWN_COMMANDS.get(normalized)
    if exact:
        return {"intent": exact, "source": "exact"}

    input_tokens = _important_tokens(normalized)

    # Frases de voz quase sempre recebem palavras extras, por exemplo
    # "quero abrir os produtos". Quando todos os termos relevantes de uma
    # frase oficial estão presentes, ela é uma ação conhecida — sem depender
    # da probabilidade baixa do classificador com dezenas de intenções.
    for phrase, intent in KNOWN_COMMANDS.items():
        phrase_tokens = _important_tokens(phrase)
        if len(phrase_tokens) >= 2 and phrase_tokens.issubset(input_tokens):
            return {
                "intent": intent,
                "source": "contains-known-command",
                "matched_phrase": phrase,
            }

    best_phrase = None
    best_intent = None
    best_score = 0.0

    for phrase, intent in KNOWN_COMMANDS.items():
        phrase_tokens = _important_tokens(phrase)
        overlap = len(input_tokens & phrase_tokens) / max(len(input_tokens | phrase_tokens), 1)
        score = SequenceMatcher(None, normalized, phrase).ratio()

        if overlap < 0.5 or score <= best_score:
            continue

        best_phrase = phrase
        best_intent = intent
        best_score = score

    if best_intent and best_score >= FUZZY_MATCH_THRESHOLD:
        return {
            "intent": best_intent,
            "source": "fuzzy",
            "matched_phrase": best_phrase,
            "score": best_score,
        }

    return None
