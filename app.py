import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

# Controllers import
from controllers.embed_controller import embed_file
from controllers.chat_controller import (
    query_old_controller,
    new_chat_controller,
    continue_chat_controller,
    list_chats_controller,
    get_chat_controller,
    delete_chat_controller
)


TEMP_FOLDER = os.getenv('TEMP_FOLDER')
os.makedirs(TEMP_FOLDER, exist_ok=True)

app = Flask(__name__)
CORS(app)

@app.route('/embed', methods=['POST'])
def route_embed():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    result = embed_file(file)
    if result:
        return jsonify({"success": "File added successfully"}), 200
    return jsonify({"error": "File added unsuccessfully"}), 400

@app.route('/query', methods=['POST'])
def route_query_old():
    data = request.get_json()
    response = query_old_controller(data.get('message'))
    if response:
        return jsonify({"answer": response}), 200
    else:
        return jsonify({"error": "Something went wrong"}), 400

@app.route('/chats/new', methods=['POST'])
def route_new_chat():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Parâmetro 'user_id' é obrigatório"}), 400
    data = request.get_json()
    response = new_chat_controller(user_id, data.get('message'))
    if response:
        return jsonify({"answer": response}), 200
    else:
        return jsonify({"error": "Something went wrong"}), 400

@app.route('/chats/<chat_id>/add', methods=['POST'])
def route_resume_chat(chat_id):
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Parâmetro 'user_id' é obrigatório"}), 400
    data = request.get_json()
    message = data.get('message')
    response = continue_chat_controller(user_id, chat_id, message)
    if response:
        return jsonify({"answer": response}), 200
    else:
        return jsonify({"error": "Something went wrong"}), 400

@app.route('/chats', methods=['GET'])
def route_list_chats():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Parâmetro 'user_id' é obrigatório"}), 400
    return jsonify(list_chats_controller(user_id))

@app.route('/chats/<chat_id>', methods=['GET'])
def get_chat(chat_id):
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Parâmetro 'user_id' é obrigatório"}), 400
    chat = get_chat_controller(user_id, chat_id)
    if not chat:
        return jsonify({"error": "Conversa não encontrada"}), 404
    return jsonify(chat), 200

@app.route('/chats/<chat_id>/delete', methods=['DELETE'])
def delete_chat(chat_id):
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Parâmetro 'user_id' é obrigatório"}), 400
    result = delete_chat_controller(user_id, chat_id)
    if result:
        return jsonify({"success": "Conversa deletada com sucesso"}), 200
    else:
        return jsonify({"error": "Erro ao deletar conversa"}), 500

if __name__ == "__main__":
    app.run()
