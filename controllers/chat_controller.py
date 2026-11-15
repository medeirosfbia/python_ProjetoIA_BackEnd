from flask import Response, jsonify, request

from services.auth_service import authenticated_user_id
from services.chat_service import (
    ChatNotFoundError,
    InvalidModelError,
    NoTutorForSubjectError,
    QuestionNotFoundError,
    QuestionNotGradedError,
    continue_chat,
    explain_question,
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

    try:
        response = query_new_chat(authenticated_user_id(), model, message)
    except InvalidModelError as error:
        return jsonify({"error": str(error)}), 400
    return _stream_response(response)


def continue_chat_controller(chat_id):
    data = _request_data()
    model = data.get("model")
    message = data.get("message")

    # model é opcional: a conversa já guarda o tutor (exigido só em conversas antigas)
    if not message:
        return jsonify({"error": "message é obrigatório"}), 400

    try:
        response = continue_chat(
            authenticated_user_id(), chat_id, model, message
        )
    except InvalidModelError as error:
        return jsonify({"error": str(error)}), 400
    except ChatNotFoundError:
        return jsonify({"error": "Conversa não encontrada"}), 404
    return _stream_response(response)


def explain_question_controller():
    data = _request_data()
    prova_id = data.get("prova_id")
    id_questao = data.get("id_questao")

    if not prova_id or not id_questao:
        return jsonify({"error": "prova_id e id_questao são obrigatórios"}), 400

    try:
        response = explain_question(
            authenticated_user_id(), prova_id, id_questao,
            model=data.get("model"), query=data.get("message"),
        )
    except (InvalidModelError, NoTutorForSubjectError) as error:
        return jsonify({"error": str(error)}), 400
    except QuestionNotFoundError:
        return jsonify({"error": "Questão não encontrada nas suas tentativas"}), 404
    except QuestionNotGradedError:
        return jsonify({"error": "Questão ainda não corrigida"}), 409
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
