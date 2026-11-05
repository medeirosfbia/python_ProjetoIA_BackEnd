import logging
import ollama
from models import exam as exam_model
from models.history import (
    create_chat,
    update_chat,
    list_last_chats,
    get_chat_info,
    get_chat_messages,
    delete_conversation
)
from services import tutor_context
from services.dashboard_service import subject_key, subject_snapshot

logger = logging.getLogger(__name__)

math_context = "Você é um assistente especializado em resolver problemas matemáticos. Responda com o passo a passo de forma clara e concisa. Responda sempre em Português Brasileiro e organize em MarkDown. Nunca dê a resposta ao final, apenas o passo a passo. Se não souber a resposta, diga que não sabe. Caso a pergunta não tenha relação com matemática, diga que não sabe e não tente responder."
english_context = "You are an assistant specialized in helping with english study. Answer with a clear and concise step-by-step explanation. Prefer to respond in english but translate if the student is facing dificulties. Never provide the final answer, only the step-by-step process. If you don't know the answer, say that you don't know. If the question is related to mathematics, say that you don't know and do not attempt to answer."

# Tutores aceitos pela API: id enviado pelos apps -> modelo do Ollama, prompt,
# matéria (chave de subject_key) e idioma dos textos extras do prompt
TUTORES = {
    "qwen2-math": {"ollama_model": "qwen2-math", "system_prompt": math_context,
                   "materia": "matematica", "idioma": "pt"},
    "llama3": {"ollama_model": "llama3", "system_prompt": english_context,
               "materia": "ingles", "idioma": "en"},
}
HISTORICO_MAX_MENSAGENS = 10
MENSAGEM_ERRO = "Ocorreu um erro ao gerar a resposta."


class ChatNotFoundError(LookupError):
    pass


class InvalidModelError(ValueError):
    def __init__(self, model):
        super().__init__(f"model deve ser um de: {', '.join(TUTORES)}")
        self.model = model


class QuestionNotFoundError(LookupError):
    pass


class QuestionNotGradedError(Exception):
    pass


class NoTutorForSubjectError(ValueError):
    def __init__(self, assunto):
        super().__init__(f"Não há tutor para a matéria {assunto}; informe model")
        self.assunto = assunto


def _tutor(model):
    if model not in TUTORES:
        raise InvalidModelError(model)
    return TUTORES[model]


def tutor_for_subject(assunto):
    materia = subject_key(assunto)
    return next((model for model, tutor in TUTORES.items() if tutor["materia"] == materia), None)


def _student_context(user_id, tutor):
    # Personalização é um extra: qualquer falha só faz o tutor responder sem ela
    try:
        snapshot = subject_snapshot(user_id, tutor["materia"])
        return tutor_context.student_context(snapshot, tutor["idioma"])
    except Exception:
        logger.exception("Falha ao montar o perfil do aluno para o tutor")
        return None


def _system_prompt(tutor, context):
    partes = [tutor["system_prompt"], context.get("student"), context.get("question")]
    return "\n\n".join(parte for parte in partes if parte)


def _start_chat(user_id, model, tutor, query, title, context, origin=None):
    context = {chave: valor for chave, valor in context.items() if valor}
    messages = [
        {"role": "system", "content": _system_prompt(tutor, context)},
        {"role": "user", "content": query}
    ]

    chat_id = create_chat(user_id, title=title, model=model, context=context, origin=origin)
    update_chat(user_id, chat_id, "user", query)

    return {
        "chat_id": chat_id,
        "resposta_stream": _stream_and_save(user_id, chat_id, messages, tutor["ollama_model"])
    }


def generate_streamed_response(messages, ollama_model):
    stream = ollama.chat(model=ollama_model, messages=messages, stream=True)
    # O gerador vai 'yield' cada pedaço da resposta à medida que chega
    for chunk in stream:
        yield chunk['message']['content']


def _stream_and_save(user_id, chat_id, messages, ollama_model):
    """Repassa o stream ao cliente e grava a resposta só se ela vier completa."""
    full_response_content = []
    try:
        for chunk in generate_streamed_response(messages, ollama_model):
            full_response_content.append(chunk)
            yield chunk
    except Exception:
        logger.exception("Erro ao consultar o modelo %s", ollama_model)
        # A mensagem de erro vai para o cliente, mas não entra no histórico
        yield MENSAGEM_ERRO
        return

    update_chat(user_id, chat_id, "assistant", "".join(full_response_content))


def query_new_chat(user_id: str, model: str, query: str):
    tutor = _tutor(model)
    # O perfil é calculado na criação e salvo na conversa: o tutor não muda de
    # comportamento no meio dela e não recalculamos a cada mensagem
    return _start_chat(
        user_id, model, tutor, query,
        title=f'{query.capitalize()[:30]}...',
        context={"student": _student_context(user_id, tutor)},
    )


def explain_question(user_id: str, prova_id: str, id_questao: str, model: str = None, query: str = None):
    """Abre uma conversa sobre uma questão da última tentativa do usuário na prova."""
    tentativas = exam_model.list_answers({"usuario_id": user_id, "prova_id": prova_id}, limit=1)
    item = next(
        (i for i in (tentativas[0]["respostas"] if tentativas else []) if i["id_questao"] == id_questao),
        None,
    )
    exam = exam_model.get_exam(prova_id)
    questao = next(
        (q for q in (exam or {}).get("questoes", []) if q["id_questao"] == id_questao),
        None,
    )
    if not item or not questao:
        raise QuestionNotFoundError(f"{prova_id}/{id_questao}")
    if item.get("status_correcao") == "pendente":
        raise QuestionNotGradedError(id_questao)

    if not model:
        assunto = exam.get("contexto", {}).get("assunto_materia")
        model = tutor_for_subject(assunto)
        if not model:
            raise NoTutorForSubjectError(assunto)
    tutor = _tutor(model)

    return _start_chat(
        user_id, model, tutor,
        query or tutor_context.default_question_message(item, tutor["idioma"]),
        title=f"Revisão: {exam.get('titulo', '')}"[:40],
        context={
            "student": _student_context(user_id, tutor),
            "question": tutor_context.question_context(exam, questao, item, tutor["idioma"]),
        },
        origin={"prova_id": prova_id, "id_questao": id_questao},
    )


def continue_chat(user_id: str, chat_id: str, model: str, query: str):
    try:
        chat = get_chat_messages(user_id, chat_id)
    except ValueError as error:
        raise ChatNotFoundError(chat_id) from error

    # O tutor é o da conversa; o model enviado só vale para conversas antigas, sem tutor salvo
    tutor = _tutor(chat.get("model") or model)

    messages = [{"role": "system", "content": _system_prompt(tutor, chat.get("context") or {})}]
    # Só role/content: o histórico guarda também o timestamp de cada mensagem
    messages.extend(
        {"role": message["role"], "content": message["content"]}
        for message in chat["messages"][-HISTORICO_MAX_MENSAGENS:]
    )
    messages.append({"role": "user", "content": query})

    update_chat(user_id, chat_id, "user", query)

    return {
        "chat_id": chat_id,
        "resposta_stream": _stream_and_save(user_id, chat_id, messages, tutor["ollama_model"])
    }

def add_messages(user_id, chat_id, query, model_response):
    update_chat(user_id, chat_id, "user", query)
    update_chat(user_id, chat_id, "assistant", model_response)

# def query_new_chat(user_id: str, model:str, query: str) -> str:
#     try:
#         if model:
#             LLM_MODEL = model
            
#         if model == "math":
#             context = math_context
#         elif model == "english":
#             context = english_context
        
        
#         response = ollama.chat(model=LLM_MODEL, messages=[
#             {
#                 "role": "system",
#                 'content': context,
#             },
#             {"role": "user", "content": query}
#         ])
#         model_response = response['message']['content']
#     except Exception as e:
#         print(f"Erro ao consultar o modelo: {e}")
#         raise
#     chat_id = create_chat(user_id, title=f'{query.capitalize()[:30]}...')
#     add_messages(user_id, chat_id, query, model_response)
#     return {
#         "chat_id": chat_id,
#         "resposta": model_response
#     }

# def continue_chat(user_id: str, chat_id: str, model:str, query: str) -> str:
#     chat = get_chat_messages(user_id, chat_id)
    
#     if model == "math":
#             context = math_context
#     elif model == "english":
#             context = english_context
            
#     messages = [{
#         "role": "system", 
#         "content": context}]
#     messages.extend(chat["messages"][-10:])
#     messages.append({"role": "user", "content": query})
#     try:
#         if model:
#             LLM_MODEL = model
#         response = ollama.chat(model=LLM_MODEL, messages=messages)
#         model_response = response['message']['content']
#         add_messages(user_id, chat_id, query, model_response)
#         return model_response
#     except Exception as e:
#         print(f"Erro ao consultar o modelo: {e}")
#         raise
