from flask import Response, jsonify, request

from services.auth_service import authenticated_user_id
from services.chat_service import (
    continue_chat,
    delete_conversation,
    get_chat_info,
    list_last_chats,
    query_new_chat,
)


def _request_data():
    return request.get_json(silent=True) or {}


def _stream_response(response):
    if not response:
        return jsonify({"error": "Something went wrong"}), 400

    return Response(
        response["resposta_stream"],
        mimetype="text/plain",
        headers={"X-Chat-ID": response["chat_id"]},
    )


def new_chat_controller():
    data = _request_data()
    model = data.get("model")
    message = data.get("message")

    if not model or not message:
        return jsonify({"error": "model e message são obrigatórios"}), 400

    response = query_new_chat(authenticated_user_id(), model, message)
    return _stream_response(response)


def continue_chat_controller(chat_id):
    data = _request_data()
    model = data.get("model")
    message = data.get("message")

    if not model or not message:
        return jsonify({"error": "model e message são obrigatórios"}), 400

    response = continue_chat(
        authenticated_user_id(), chat_id, model, message
    )
    return _stream_response(response)


def list_chats_controller():
    return jsonify(list_last_chats(authenticated_user_id()))


def get_chat_controller(chat_id):
    chat = get_chat_info(authenticated_user_id(), chat_id)
    if not chat:
        return jsonify({"error": "Conversa não encontrada"}), 404
    return jsonify(chat), 200


def delete_chat_controller(chat_id):
    result = delete_conversation(authenticated_user_id(), chat_id)
    if result:
        return jsonify({"success": "Conversa deletada com sucesso"}), 200
    return jsonify({"error": "Erro ao deletar conversa"}), 500
