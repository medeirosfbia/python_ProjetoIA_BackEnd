import os
import ollama
from models.history import (
    create_chat,
    update_chat,
    list_last_chats,
    get_chat_info,
    get_chat_messages,
    delete_conversation
)

# LLM_MODEL = os.getenv('LLM_MODEL')
math_context = "Você é um assistente especializado em resolver problemas matemáticos. Responda com o passo a passo de forma clara e concisa. Responda sempre em Português Brasileiro e organize em MarkDown. Nunca dê a resposta ao final, apenas o passo a passo. Se não souber a resposta, diga que não sabe. Caso a pergunta não tenha relação com matemática, diga que não sabe e não tente responder."
english_context = "You are an assistant specialized in helping with english study. Answer with a clear and concise step-by-step explanation. Prefer to respond in english but translate if the student is facing dificulties. Never provide the final answer, only the step-by-step process. If you don't know the answer, say that you don't know. If the question is related to mathematics, say that you don't know and do not attempt to answer."

def generate_streamed_response(messages, model):
    try:
        stream = ollama.chat(model=model, messages=messages, stream=True)
        
        # O gerador vai 'yield' cada pedaço da resposta à medida que chega
        for chunk in stream: 
            # O 'chunk' é um dicionário, o texto está em ['content']
            yield chunk['message']['content']
            
    except Exception as e:
        print(f"Erro ao consultar o modelo: {e}")
        # Você pode 'yield' uma mensagem de erro para o frontend
        yield "Ocorreu um erro ao gerar a resposta."

def query_new_chat(user_id: str, model: str, query: str):
    # if model:
    #     LLM_MODEL = model       
    if model == "qwen2-math":
        context = math_context
    elif model == "llama3":
         context = english_context

    messages = [
        {
            "role": "system",
            'content': context,
        },
        {"role": "user", "content": query}
    ]

    
    chat_id = create_chat(user_id, title=f'{query.capitalize()[:30]}...')
    update_chat(user_id, chat_id, "user", query)

    full_response_content = []

    def stream_and_save_response():
        # Este gerador vai ser usado na rota Flask
        for chunk in generate_streamed_response(messages, model):
            full_response_content.append(chunk)
            yield chunk
        
        # Salva a resposta completa no banco de dados após o stream terminar
        model_response = "".join(full_response_content)
        update_chat(user_id, chat_id, "assistant", model_response)

    return {
        "chat_id": chat_id,
        "resposta_stream": stream_and_save_response() 
    }

def continue_chat(user_id: str, chat_id: str, model: str, query: str):
    chat = get_chat_messages(user_id, chat_id)

    # if model:
    #     LLM_MODEL = model
    if model == "qwen2-math":
            context = math_context
    elif model == "llama3":
            context = english_context

    messages = [
        {
            "role": "system", 
            "content": context
        }
    ]
    messages.extend(chat["messages"][-10:])
    messages.append({"role": "user", "content": query})
    
    update_chat(user_id, chat_id, "user", query)
    
    full_response_content = []

    def stream_and_save_response():
        for chunk in generate_streamed_response(messages, model):
            full_response_content.append(chunk)
            yield chunk
            
        model_response = "".join(full_response_content)
        update_chat(user_id, chat_id, "assistant", model_response)

    return {
        "chat_id": chat_id,
        "resposta_stream": stream_and_save_response() 
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
