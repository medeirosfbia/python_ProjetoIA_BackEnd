import os
import ollama
from history import *
# from dotenv import load_dotenv

# load_dotenv()

LLM_MODEL = os.getenv('LLM_MODEL')

# from langchain_community.chat_models import ChatOllama
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.runnables import RunnablePassthrough
# from addDocuments import 

# def query(query):
#     local_model = ChatOllama(model='qwen2')
#     template = '{prompt} -- answer in less than 45 words'
#     prompt = ChatPromptTemplate.from_template(template)
#     chain = prompt | local_model | StrOutputParser()

#     return chain.invoke({'prompt':query})

# def query2(query):
#     local_model = ChatOllama(model='qwen2')
    
#     # Criar um retriever para receber documentos relevantes quando fazemos uma pergunta
#     retriever = vectorstore.as_retriever()

#     rag_template = '''
#     Answer the question based only on the following context: {context}
#     Question: {question} - Answer in less than 60 words
#     '''
#     rag_prompt = ChatPromptTemplate.from_template(rag_template)
#     rag_chain = (
#         {
#             'context' : retriever,
#             'question' : RunnablePassthrough()
#         }
#         | rag_prompt
#         | local_model
#         | StrOutputParser()
#     ) 

#     return rag_chain.invoke(query)

# def build_chat_history(user_id, new_message):
#     """Constroi o histórico de mensagens no formato Ollama a partir do MongoDB."""
#     history = get_conversation_history(user_id)
#     messages = [
#         {
#             'role' : 'system',
#             'content': 'Você é um assistente especializado em resolver problemas matemáticos. Responda com o passo a passo de forma clara e concisa. Responda sempre em Português Brasileiro',
#         },
#     ]

#     for conv in history:
#         for msg in conv['messages']:
#             messages.append({
#                 'role': msg['role'],
#                 'content': msg['content']
#             })

#     messages.append({
#         'role': 'user',
#         'content': new_message
#     })
#     return messages

# def query(user_id, query):

#     # Recupera histórico e envia ao Ollama
#     messages = build_chat_history(user_id, query)

#     try:
#         response = ollama.chat(model=LLM_MODEL, messages=messages)
#         model_response = response['message']['content']
    
#         # Salva no MongoDB
#         save_conversation(user_id, query, model_response)
#         return model_response

#     except Exception as e:
#         print(f"Erro ao consultar o modelo: {e}")
#         raise

# user_id = "aluno123"
# pergunta = "Qual é a integral de 2x dx?"
# resposta = query(user_id, pergunta)
# print(f"Assistente: {resposta}")


def query_old(query):
    response = ollama.chat(model='qwen2', messages=[
        {
            'role' : 'system',
            'content': 'Você é um assistente especializado em resolver problemas matemáticos. Responda com o passo a passo de forma clara e concisa. Responda sempre em Português Brasileiro',
        },
        {
            'role':'user',
            'content': query,  
        },
    ])

    return response['message']['content']




def add_messages(user_id, chat_id, query, model_response):
        update_chat(user_id, chat_id, "user", query)
        update_chat(user_id, chat_id, "assistant", model_response)



def query_new_chat(user_id: str, query: str) -> str:


    try:
        response = ollama.chat(model=LLM_MODEL, messages=[
            {
                "role": "system",
                'content': 'Você é um assistente especializado em resolver problemas matemáticos. Responda com o passo a passo de forma clara e concisa. Responda sempre em Português Brasileiro',
            },
            {"role": "user", "content": query}
        ])
        model_response = response['message']['content']

    except Exception as e:
        print(f"Erro ao consultar o modelo: {e}")
        raise

        # Cria nova conversa
    chat_id = create_chat(user_id, title = f'{query.capitalize()[:30]}...')

    # Salva ambas as mensagens
    add_messages(user_id, chat_id, query, model_response)

    return {
        "chat_id": chat_id,
        "resposta": model_response
    }



def continue_chat(user_id: str, chat_id: str, query: str) -> str:
    # Recupera histórico
    chat = get_chat_messages(user_id, chat_id)


    # Prepara contexto
    messages = [{"role": "system", "content": "Continue a explicação matemática:"}]
    messages.extend(chat["messages"][-10:])  # Últimas 10 mensagens
    messages.append({"role": "user", "content": query})

    try:
        response = ollama.chat(model=LLM_MODEL, messages=messages)
        model_response = response['message']['content']
    
        # Salva no MongoDB
        add_messages(user_id, chat_id, query, model_response)
        return model_response

    except Exception as e:
        print(f"Erro ao consultar o modelo: {e}")
        raise
