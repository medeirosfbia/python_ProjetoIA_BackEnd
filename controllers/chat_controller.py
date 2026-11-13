from flask import Response, jsonify, request

from services.auth_service import authenticated_user_id
from services.chat_service import (
    ChatModelConflictError,
    ChatModelRequiredError,
    continue_chat,
    delete_conversation,
    get_chat_info,
    list_last_chats,
    query_new_chat,
)
from models.history import associate_chat_model
from services.tutor_service import InvalidTutorModel, resolve_tutor


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

    try:
        # Validação vem antes de criar o chat ou publicar evento.
        resolve_tutor(model)
        response = query_new_chat(authenticated_user_id(), model, message)
    except InvalidTutorModel:
        return jsonify({"error": "Modelo inválido", "code": "INVALID_CHAT_MODEL"}), 400
    return _stream_response(response)


def continue_chat_controller(chat_id):
    data = _request_data()
    model = data.get("model")
    message = data.get("message")

    if not message:
        return jsonify({"error": "message é obrigatório"}), 400

    try:
        if model is not None:
            resolve_tutor(model)
        response = continue_chat(authenticated_user_id(), chat_id, model, message)
    except InvalidTutorModel:
        return jsonify({"error": "Modelo inválido", "code": "INVALID_CHAT_MODEL"}), 400
    except ChatModelRequiredError:
        return jsonify({"error": "Associe um modelo ao chat antes de continuar", "code": "CHAT_MODEL_REQUIRED"}), 409
    except ChatModelConflictError:
        return jsonify({"error": "O modelo informado difere do tutor do chat", "code": "CHAT_MODEL_CONFLICT"}), 409
    except ValueError:
        return jsonify({"error": "Conversa não encontrada"}), 404
    return _stream_response(response)


def associate_chat_model_controller(chat_id):
    model = _request_data().get("model")
    try:
        resolve_tutor(model)
    except InvalidTutorModel:
        return jsonify({"error": "Modelo inválido", "code": "INVALID_CHAT_MODEL"}), 400

    chat, conflict = associate_chat_model(authenticated_user_id(), chat_id, model)
    if chat is None:
        return jsonify({"error": "Conversa não encontrada"}), 404
    if conflict:
        return jsonify({"error": "O tutor do chat já foi definido", "code": "CHAT_MODEL_CONFLICT"}), 409
    return jsonify(chat), 200


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
