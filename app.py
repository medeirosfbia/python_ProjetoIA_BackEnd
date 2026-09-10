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

TEMP_FOLDER = os.getenv('TEMP_FOLDER')
os.makedirs(TEMP_FOLDER, exist_ok=True)


app = Flask(__name__)
CORS(
    app,
    origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_headers=["Authorization", "Content-Type"],
    methods=["GET", "POST", "DELETE", "OPTIONS"],
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

if __name__ == "__main__":
    app.run()
