import logging
import ollama
from models.history import (
    create_chat,
    update_chat,
    list_last_chats,
    get_chat_info,
    get_chat_messages,
    delete_conversation
)

logger = logging.getLogger(__name__)

math_context = "Você é um assistente especializado em resolver problemas matemáticos. Responda com o passo a passo de forma clara e concisa. Responda sempre em Português Brasileiro e organize em MarkDown. Nunca dê a resposta ao final, apenas o passo a passo. Se não souber a resposta, diga que não sabe. Caso a pergunta não tenha relação com matemática, diga que não sabe e não tente responder."
english_context = "You are an assistant specialized in helping with english study. Answer with a clear and concise step-by-step explanation. Prefer to respond in english but translate if the student is facing dificulties. Never provide the final answer, only the step-by-step process. If you don't know the answer, say that you don't know. If the question is related to mathematics, say that you don't know and do not attempt to answer."

# Tutores aceitos pela API: id enviado pelos apps -> modelo do Ollama e prompt
TUTORES = {
    "qwen2-math": {"ollama_model": "qwen2-math", "system_prompt": math_context},
    "llama3": {"ollama_model": "llama3", "system_prompt": english_context},
}
HISTORICO_MAX_MENSAGENS = 10
MENSAGEM_ERRO = "Ocorreu um erro ao gerar a resposta."


class ChatNotFoundError(LookupError):
    pass


class InvalidModelError(ValueError):
    def __init__(self, model):
        super().__init__(f"model deve ser um de: {', '.join(TUTORES)}")
        self.model = model


def _tutor(model):
    if model not in TUTORES:
        raise InvalidModelError(model)
    return TUTORES[model]


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
    messages = [
        {"role": "system", "content": tutor["system_prompt"]},
        {"role": "user", "content": query}
    ]

    chat_id = create_chat(user_id, title=f'{query.capitalize()[:30]}...', model=model)
    update_chat(user_id, chat_id, "user", query)

    return {
        "chat_id": chat_id,
        "resposta_stream": _stream_and_save(user_id, chat_id, messages, tutor["ollama_model"])
    }


def continue_chat(user_id: str, chat_id: str, model: str, query: str):
    try:
        chat = get_chat_messages(user_id, chat_id)
    except ValueError as error:
        raise ChatNotFoundError(chat_id) from error

    # O tutor é o da conversa; o model enviado só vale para conversas antigas, sem tutor salvo
    tutor = _tutor(chat.get("model") or model)

    messages = [{"role": "system", "content": tutor["system_prompt"]}]
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
