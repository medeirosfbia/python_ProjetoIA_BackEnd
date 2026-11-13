"""Contrato dos tutores públicos e dos modelos reais executados no Ollama."""
import os


class InvalidTutorModel(ValueError):
    pass


_TUTORS = {
    "llama3": {
        "environment": "OLLAMA_ENGLISH_MODEL", "default": "llama3",
        "context": "You are an assistant specialized in helping with english study. Answer with a clear and concise step-by-step explanation. Prefer to respond in english but translate if the student is facing difficulties. Never provide the final answer, only the step-by-step process. If you don't know the answer, say that you don't know. If the question is related to mathematics, say that you don't know and do not attempt to answer.",
    },
    "qwen2-math": {
        "environment": "OLLAMA_MATH_MODEL", "default": "qwen2-math",
        "context": "Você é um assistente especializado em resolver problemas matemáticos. Responda com o passo a passo de forma clara e concisa. Responda sempre em Português Brasileiro e organize em MarkDown. Nunca dê a resposta ao final, apenas o passo a passo. Se não souber a resposta, diga que não sabe. Caso a pergunta não tenha relação com matemática, diga que não sabe e não tente responder.",
    },
}


def resolve_tutor(public_model: str) -> dict:
    """Resolve exclusivamente os aliases públicos documentados pela API."""
    tutor = _TUTORS.get(public_model)
    if not tutor:
        raise InvalidTutorModel(public_model)
    return {
        "model": public_model,
        "ollama_model": os.getenv(tutor["environment"], tutor["default"]),
        "context": tutor["context"],
    }
