"""Smoke test local do adaptador Ollama, sem banco ou credenciais de usuário."""
import sys
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from timo.conversation import chat, enabled  # noqa: E402


def main():
    if not enabled():
        print("TIMO_OLLAMA_ENABLED=false; conversa desativada pela configuração do servidor.")
        return 0
    started = perf_counter()
    result = chat("Olá, Timo! Responda com uma saudação curta em português.", [])
    print(f"TIMO Ollama: {result['conversation_status']} ({perf_counter() - started:.2f}s)")
    if not result["success"]:
        return 1
    print(result["message"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
