import os
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from configs import swagger_config
from flasgger import Swagger
from services.auth_service import authenticate_request
load_dotenv()
from controllers.chat_controller import (
    new_chat_controller,
    continue_chat_controller,
    list_chats_controller,
    get_chat_controller,
    delete_chat_controller,
)
from controllers.exam_controller import (
    list_exams_controller,
    get_exam_controller,
    create_exam_controller,
    update_exam_controller,
    delete_exam_controller,
    submit_answers_controller,
    list_my_exam_answers_controller,
    list_all_exam_answers_controller,
    list_my_answers_history_controller,
)

TEMP_FOLDER = os.getenv('TEMP_FOLDER')
os.makedirs(TEMP_FOLDER, exist_ok=True)


app = Flask(__name__)
CORS(
    app,
    origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_headers=["Authorization", "Content-Type"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    expose_headers=["X-Chat-ID"],
)


@app.before_request
def require_authentication():
    return authenticate_request()


@app.errorhandler(PermissionError)
def handle_permission_error(error):
    return jsonify({"error": str(error)}), 403

swagger = Swagger(app, template=swagger_config.swagger_template, config=swagger_config.swagger_config)

        
@app.route('/chats/new', methods=['POST'])
def route_new_chat():
    return new_chat_controller()

        
@app.route('/chats/<chat_id>/add', methods=['POST'])
def route_resume_chat(chat_id):
    return continue_chat_controller(chat_id)
        
@app.route('/chats', methods=['GET'])
def route_list_chats():
    return list_chats_controller()

@app.route('/chats/<chat_id>', methods=['GET'])
def get_chat(chat_id):
    return get_chat_controller(chat_id)

@app.route('/chats/<chat_id>/delete', methods=['DELETE'])
def delete_chat(chat_id):
    return delete_chat_controller(chat_id)


@app.route('/exams', methods=['GET'])
def route_list_exams():
    return list_exams_controller()

@app.route('/exams', methods=['POST'])
def route_create_exam():
    return create_exam_controller()

# Rota estática; o Flask a prioriza sobre /exams/<exam_id>
@app.route('/exams/answers', methods=['GET'])
def route_my_answers_history():
    return list_my_answers_history_controller()

@app.route('/exams/<exam_id>', methods=['GET'])
def route_get_exam(exam_id):
    return get_exam_controller(exam_id)

@app.route('/exams/<exam_id>', methods=['PUT'])
def route_update_exam(exam_id):
    return update_exam_controller(exam_id)

@app.route('/exams/<exam_id>', methods=['DELETE'])
def route_delete_exam(exam_id):
    return delete_exam_controller(exam_id)

@app.route('/exams/<exam_id>/answers', methods=['POST'])
def route_submit_answers(exam_id):
    return submit_answers_controller(exam_id)

@app.route('/exams/<exam_id>/answers', methods=['GET'])
def route_my_exam_answers(exam_id):
    return list_my_exam_answers_controller(exam_id)

@app.route('/exams/<exam_id>/answers/all', methods=['GET'])
def route_all_exam_answers(exam_id):
    return list_all_exam_answers_controller(exam_id)

if __name__ == "__main__":
    app.run()
