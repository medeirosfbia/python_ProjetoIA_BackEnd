"""Grava (ou atualiza) a prova de exemplo no MongoDB configurado no .env.

Uso, a partir da raiz do projeto:
    python -m seeds.seed_exam_example
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from models.exam import get_exam, replace_exam  # noqa: E402
from services.exam_service import build_exam_document, validate_exam_payload  # noqa: E402

EXAMPLE_EXAM_ID = "prova_exemplo_matematica_001"
EXAMPLE_FILE = Path(__file__).with_name("exam_example.json")


def main():
    campos = validate_exam_payload(json.loads(EXAMPLE_FILE.read_text(encoding="utf-8")))

    # Mantém a data de criação original se a prova já tiver sido gravada antes
    existente = get_exam(EXAMPLE_EXAM_ID)
    data_criacao = (
        existente["contexto"]["data_criacao"] if existente else datetime.now(timezone.utc)
    )

    exam = build_exam_document(EXAMPLE_EXAM_ID, campos, "seed", data_criacao, "seed")
    replace_exam(exam, upsert=True)
    acao = "atualizada" if existente else "criada"
    print(f"Prova de exemplo '{EXAMPLE_EXAM_ID}' {acao} com {exam['total_questoes']} questões.")


if __name__ == "__main__":
    main()
