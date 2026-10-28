from flask import jsonify, request

from services.auth_service import authenticated_user_id, is_admin
from services.exam_service import (
    ExamConflictError,
    ExamValidationError,
    create_exam,
    delete_exam,
    get_exam,
    list_exam_answers,
    list_exams,
    list_user_answers,
    submit_answers,
    update_exam,
)


def _request_data():
    return request.get_json(silent=True)


def _forbidden():
    return jsonify({"error": "Acesso restrito a administradores"}), 403


def _not_found():
    return jsonify({"error": "Prova não encontrada"}), 404


def _validation_error(error):
    return jsonify({"error": "Dados inválidos", "detalhes": error.errors}), 400


def list_exams_controller():
    exams = list_exams(
        is_admin(),
        assunto=request.args.get("assunto"),
        status=request.args.get("status"),
    )
    return jsonify(exams), 200


def get_exam_controller(exam_id):
    exam = get_exam(exam_id, is_admin())
    if not exam:
        return _not_found()
    return jsonify(exam), 200


def create_exam_controller():
    if not is_admin():
        return _forbidden()
    try:
        exam = create_exam(authenticated_user_id(), _request_data())
    except ExamValidationError as error:
        return _validation_error(error)
    return jsonify(exam), 201


def update_exam_controller(exam_id):
    if not is_admin():
        return _forbidden()
    try:
        exam = update_exam(exam_id, authenticated_user_id(), _request_data())
    except ExamValidationError as error:
        return _validation_error(error)
    if not exam:
        return _not_found()
    return jsonify(exam), 200


def delete_exam_controller(exam_id):
    if not is_admin():
        return _forbidden()
    if not delete_exam(exam_id):
        return _not_found()
    return jsonify({"success": "Prova deletada com sucesso"}), 200


def submit_answers_controller(exam_id):
    try:
        answer = submit_answers(
            exam_id, authenticated_user_id(), is_admin(), _request_data()
        )
    except ExamValidationError as error:
        return _validation_error(error)
    except ExamConflictError as error:
        return jsonify({"error": str(error)}), 409
    if not answer:
        return _not_found()
    return jsonify(answer), 201


def list_my_exam_answers_controller(exam_id):
    return jsonify(list_user_answers(authenticated_user_id(), exam_id)), 200


def list_all_exam_answers_controller(exam_id):
    if not is_admin():
        return _forbidden()
    return jsonify(list_exam_answers(exam_id)), 200


def list_my_answers_history_controller():
    return jsonify(list_user_answers(authenticated_user_id())), 200
