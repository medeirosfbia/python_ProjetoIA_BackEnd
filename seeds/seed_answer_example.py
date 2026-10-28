"""Grava (ou atualiza) uma tentativa sintética da usuária MariaS na prova de exemplo.

Rode antes o seed da prova. Uso, a partir da raiz do projeto:
    python -m seeds.seed_exam_example
    python -m seeds.seed_answer_example
"""
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from models.mongo_connection import exam_answers_collection  # noqa: E402
from models.exam import count_attempts, get_exam  # noqa: E402
from seeds.seed_exam_example import EXAMPLE_EXAM_ID  # noqa: E402
from services.exam_service import grade_answers  # noqa: E402

EXAMPLE_ANSWER_ID = "resp_exemplo_marias_001"
USER_ID = "MariaS"

# Acerta q1, q3 e q4, erra q2 e responde a dissertativa (fica pendente de correção)
RESPOSTAS = {
    "respostas": [
        {"id_questao": "q1", "resposta": "op_b"},
        {"id_questao": "q2", "resposta": "op_a"},
        {"id_questao": "q3", "resposta": "op_c"},
        {"id_questao": "q4", "resposta": "op_b"},
        {
            "id_questao": "q5",
            "resposta": (
                "Na equação x² - 4x - 5 = 0 temos a = 1, b = -4 e c = -5. "
                "Calculo o discriminante: Δ = b² - 4ac = 16 + 20 = 36. "
                "Depois aplico x = (-b ± √Δ) / 2a = (4 ± 6) / 2, "
                "então x' = 10 / 2 = 5 e x'' = -2 / 2 = -1."
            ),
        },
    ],
    "tempo_gasto_segundos": 1380,
}


def main():
    exam = get_exam(EXAMPLE_EXAM_ID)
    if not exam:
        raise SystemExit(
            f"Prova '{EXAMPLE_EXAM_ID}' não encontrada; rode antes: python -m seeds.seed_exam_example"
        )

    existente = exam_answers_collection.find_one({"_id": EXAMPLE_ANSWER_ID})
    # Mantém o número da tentativa ao regravar; senão, entra como a próxima da MariaS
    tentativa = existente["tentativa"] if existente else count_attempts(EXAMPLE_EXAM_ID, USER_ID) + 1

    answer = {
        "_id": EXAMPLE_ANSWER_ID,
        "prova_id": EXAMPLE_EXAM_ID,
        "usuario_id": USER_ID,
        "tentativa": tentativa,
        "titulo_prova": exam.get("titulo"),
        "assunto_materia": exam.get("contexto", {}).get("assunto_materia"),
        "enviado_em": existente["enviado_em"] if existente else datetime.now(timezone.utc),
        **grade_answers(exam, RESPOSTAS),
    }
    exam_answers_collection.replace_one({"_id": EXAMPLE_ANSWER_ID}, answer, upsert=True)

    resultado = answer["resultado"]
    acao = "atualizada" if existente else "criada"
    print(
        f"Tentativa {tentativa} de {USER_ID} {acao}: {resultado['acertos']}/{resultado['total_questoes']} "
        f"acertos, nota {resultado['nota_obtida']}/{resultado['nota_maxima']}, "
        f"{resultado['questoes_pendentes_correcao']} questão(ões) pendente(s) de correção."
    )


if __name__ == "__main__":
    main()
