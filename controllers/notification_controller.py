from azure.core.exceptions import AzureError
from flask import jsonify, request

from services.auth_service import authenticated_user_id, is_admin
from services.notification_service import (
    NotificationValidationError,
    register_token,
    send_custom_notification,
    unregister_token,
)


def _request_data():
    return request.get_json(silent=True)


def _validation_error(error):
    return jsonify({"error": "Dados inválidos", "detalhes": error.errors}), 400


def register_token_controller():
    try:
        token = register_token(authenticated_user_id(), _request_data())
    except NotificationValidationError as error:
        return _validation_error(error)
    return jsonify(token), 201


def unregister_token_controller():
    try:
        removed = unregister_token(authenticated_user_id(), _request_data())
    except NotificationValidationError as error:
        return _validation_error(error)
    if not removed:
        return jsonify({"error": "Token não encontrado"}), 404
    return jsonify({"success": "Token removido com sucesso"}), 200


def send_notification_controller():
    if not is_admin():
        return jsonify({"error": "Acesso restrito a administradores"}), 403
    try:
        message_id = send_custom_notification(_request_data())
    except NotificationValidationError as error:
        return _validation_error(error)
    except (RuntimeError, AzureError):
        return jsonify({"error": "Fila de notificações indisponível"}), 503
    return jsonify({"messageId": message_id}), 202
