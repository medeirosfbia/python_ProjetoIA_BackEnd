from services.chat_service import (
    query_new_chat,
    continue_chat,
    list_last_chats,
    get_chat_info,
    delete_conversation
)

def new_chat_controller(user_id, model, message):
    return query_new_chat(user_id, model, message)

def continue_chat_controller(user_id, chat_id, model, message):
    return continue_chat(user_id, chat_id, model, message)

def list_chats_controller(user_id):
    return list_last_chats(user_id)

def get_chat_controller(user_id, chat_id):
    return get_chat_info(user_id, chat_id)

def delete_chat_controller(user_id, chat_id):
    return delete_conversation(user_id, chat_id)
