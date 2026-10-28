from pymongo import DESCENDING

from models.mongo_connection import exams_collection, exam_answers_collection


def list_exams(filters: dict, limit: int = 100) -> list:
    """Lista provas sem as questões (resumo para a listagem)."""
    return list(exams_collection.find(
        filters,
        {"questoes": 0}
    ).sort("contexto.data_criacao", DESCENDING).limit(limit))


def get_exam(exam_id: str):
    return exams_collection.find_one({"_id": exam_id})


def insert_exam(exam: dict):
    exams_collection.insert_one(exam)


def replace_exam(exam: dict, upsert: bool = False) -> bool:
    """Substitui a prova inteira. Retorna False se ela não existir (e upsert=False)."""
    result = exams_collection.replace_one({"_id": exam["_id"]}, exam, upsert=upsert)
    return result.matched_count == 1 or result.upserted_id is not None


def delete_exam(exam_id: str) -> bool:
    result = exams_collection.delete_one({"_id": exam_id})
    return result.deleted_count == 1


def count_attempts(exam_id: str, user_id: str) -> int:
    return exam_answers_collection.count_documents(
        {"prova_id": exam_id, "usuario_id": user_id}
    )


def insert_answer(answer: dict):
    exam_answers_collection.insert_one(answer)


def list_answers(filters: dict, include_details: bool = True, limit: int = 100) -> list:
    """Lista tentativas (mais recentes primeiro); sem detalhes retorna só o resultado."""
    projection = None if include_details else {"respostas": 0}
    return list(exam_answers_collection.find(
        filters,
        projection
    ).sort("enviado_em", DESCENDING).limit(limit))
