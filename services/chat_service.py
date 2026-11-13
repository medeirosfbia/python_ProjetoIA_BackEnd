import ollama

from models.history import create_chat, update_chat, list_last_chats, get_chat_info, get_chat_messages, delete_conversation
from services.tutor_service import resolve_tutor


class ChatModelRequiredError(Exception):
    pass


class ChatModelConflictError(Exception):
    pass


def generate_streamed_response(messages, model):
    try:
        for chunk in ollama.chat(model=model, messages=messages, stream=True):
            yield chunk["message"]["content"]
    except Exception as error:
        print(f"Erro ao consultar o modelo: {error}")
        yield "Ocorreu um erro ao gerar a resposta."


def _stream_and_save(user_id, chat_id, messages, ollama_model):
    response = []
    for chunk in generate_streamed_response(messages, ollama_model):
        response.append(chunk)
        yield chunk
    update_chat(user_id, chat_id, "assistant", "".join(response))


def query_new_chat(user_id: str, model: str, query: str):
    tutor = resolve_tutor(model)
    messages = [{"role": "system", "content": tutor["context"]}, {"role": "user", "content": query}]
    chat_id = create_chat(user_id, tutor["model"], title=f"{query.capitalize()[:30]}...")
    update_chat(user_id, chat_id, "user", query)
    return {"chat_id": chat_id, "resposta_stream": _stream_and_save(user_id, chat_id, messages, tutor["ollama_model"])}


def continue_chat(user_id: str, chat_id: str, model: str | None, query: str):
    chat = get_chat_messages(user_id, chat_id)
    persisted_model = chat.get("model")
    if not persisted_model:
        raise ChatModelRequiredError()
    tutor = resolve_tutor(persisted_model)
    if model is not None:
        # Aceita clientes legados, sem permitir uma troca silenciosa de tutor.
        resolve_tutor(model)
        if model != persisted_model:
            raise ChatModelConflictError()
    messages = [{"role": "system", "content": tutor["context"]}]
    messages.extend(chat["messages"][-10:])
    messages.append({"role": "user", "content": query})
    update_chat(user_id, chat_id, "user", query)
    return {"chat_id": chat_id, "resposta_stream": _stream_and_save(user_id, chat_id, messages, tutor["ollama_model"])}


def add_messages(user_id, chat_id, query, model_response):
    update_chat(user_id, chat_id, "user", query)
    update_chat(user_id, chat_id, "assistant", model_response)
