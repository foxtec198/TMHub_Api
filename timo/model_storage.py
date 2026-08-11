"""Caminhos do modelo de intenções do Timo.

O modelo distribuído com o código é somente leitura em produção. Treinamentos
aprovados devem ser salvos fora de ``timo/models`` para não depender da posse
dos arquivos criados pelo deploy.
"""

from os import getenv
from pathlib import Path


TIMO_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TIMO_DIR.parent
BUNDLED_MODEL_PATH = TIMO_DIR / "models" / "intent_model.pkl"
TRAINED_MODEL_PATH = Path(
    getenv("TIMO_MODEL_PATH")
    or PROJECT_DIR / "storage" / "timo" / "intent_model.pkl"
)


def active_model_path():
    """Usa o último modelo treinado; sem ele, mantém o modelo publicado."""
    return TRAINED_MODEL_PATH if TRAINED_MODEL_PATH.is_file() else BUNDLED_MODEL_PATH


def ensure_trained_model_directory():
    TRAINED_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    return TRAINED_MODEL_PATH
