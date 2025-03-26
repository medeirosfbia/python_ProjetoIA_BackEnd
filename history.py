from datetime import datetime
from typing import List, Dict
from mongo_connection import collection

def create_chat(user_id: str, title: str = None) -> str:
    """Inicia uma nova conversa para o usuário"""
    chat_id = f'chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}'

    collection.insert_one({
        "user_id" : user_id,
        "chat_id": chat_id,
        "title" : title or f"Conversa {datetime.now().strftime('%d/%m')}",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "messages": []
    })

    return chat_id


def update_chat(user_id: str, chat_id: str, role: str, content: str):
    """Adiciona uma mensagem a uma conversa específica"""
    collection.update_one(
        {"user_id": user_id, "chat_id": chat_id},
        {
            "$push": {"messages": {"role": role, "content": content, "timestamp": datetime.now()}},
            
            "$set" : {"updated_at": datetime.now()}
        })

def list_last_chats(user_id: str, limit: int = 10) -> list:
    """Lista todas as conversas do usuário (mais recentes primeiro)"""
    chats_list = list(collection.find(
        {"user_id": user_id},
        {"_id": 0, "chat_id": 1, "title": 1, "updated_at": 1}
    ).sort("updated_at", -1).limit(limit))
    
    return chats_list

def get_chat_info(user_id, chat_id):
    chat = collection.find_one({
        "user_id": user_id, # Garante que a conversa pertence ao usuário
        "chat_id": chat_id
    }, {
        "_id": 0,
        "messages": 1,
        "title": 1,
        "created_at": 1
    })

    return chat


def get_chat_messages(user_id, chat_id):
    conv = collection.find_one(
        {"user_id": user_id, "chat_id": chat_id},
        {"_id": 0, "messages": 1}
    )

    if not conv:
        raise ValueError("Conversa não encontrada")
    else:
        return conv







def save_conversation(user_id, user_message, assistant_response):
    """Salva uma interação no MongoDB."""
    conversation = {
        "user_id": user_id,
        "messages": [
            {"role": "user", "content": user_message, "timestamp": datetime.now()},
            {"role": "assistant", "content": assistant_response, "timestamp": datetime.now()}
        ],
        "last_updated": datetime.now()
    }
    collection.insert_one(conversation)

def get_conversation_history(user_id, limit=5):
    """Recupera o histórico de conversas de um usuário."""
    history = collection.find(
        {"user_id": user_id},
        {"_id": 0, "messages": 1}
    ).sort("last_updated", -1).limit(limit)
    return list(history)
