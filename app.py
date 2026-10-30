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
from controllers.material_controller import (
    list_material_folders_controller,
    list_materials_controller,
    get_material_controller,
    download_material_controller,
    create_material_controller,
    update_material_controller,
    delete_material_controller,
)

TEMP_FOLDER = os.getenv('TEMP_FOLDER')
os.makedirs(TEMP_FOLDER, exist_ok=True)


app = Flask(__name__)
# Margem de 1 MB sobre o limite dos materiais para o envelope multipart
app.config["MAX_CONTENT_LENGTH"] = (int(os.getenv("MATERIALS_MAX_SIZE_MB", "50")) + 1) * 1024 * 1024
CORS(
    app,
    origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_headers=["Authorization", "Content-Type"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    expose_headers=["X-Chat-ID", "Content-Disposition"],
)


@app.before_request
def require_authentication():
    return authenticate_request()


@app.errorhandler(PermissionError)
def handle_permission_error(error):
    return jsonify({"error": str(error)}), 403


@app.errorhandler(413)
def handle_request_too_large(error):
    return jsonify({"error": "Arquivo excede o tamanho máximo permitido"}), 413

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


# Materiais das matérias (Azure Blob). Leitura: qualquer usuário; escrita: admins.
@app.route('/materials/folders', methods=['GET'])
def route_list_material_folders():
    return list_material_folders_controller()

@app.route('/materials', methods=['GET'])
def route_list_materials():
    return list_materials_controller()

@app.route('/materials/<conteudo>', methods=['POST'])
def route_create_material(conteudo):
    return create_material_controller(conteudo)

@app.route('/materials/<conteudo>/<nome>', methods=['GET'])
def route_get_material(conteudo, nome):
    return get_material_controller(conteudo, nome)

@app.route('/materials/<conteudo>/<nome>/download', methods=['GET'])
def route_download_material(conteudo, nome):
    return download_material_controller(conteudo, nome)

@app.route('/materials/<conteudo>/<nome>', methods=['PUT'])
def route_update_material(conteudo, nome):
    return update_material_controller(conteudo, nome)

@app.route('/materials/<conteudo>/<nome>', methods=['DELETE'])
def route_delete_material(conteudo, nome):
    return delete_material_controller(conteudo, nome)

if __name__ == "__main__":
    app.run()
