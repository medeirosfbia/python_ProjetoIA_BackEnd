import os
from dotenv import load_dotenv  # Biblioteca para carregar variáveis de ambiente do arquivo .env

load_dotenv()  # Carrega as variáveis de ambiente

from flask import Flask, jsonify, request  # Importa módulos do Flask para criar a API
from flask_cors import CORS  # Importa CORS para permitir requisições de diferentes origens
from query import *  # Função importada para processar consultas
from embed import embed  # Função importada para processar a incorporação de arquivos
# from mongo_utils import save_conversation, get_conversation_history

# Obtém a pasta temporária do arquivo .env
TEMP_FOLDER = os.getenv('TEMP_FOLDER')
os.makedirs(TEMP_FOLDER, exist_ok=True)  # Cria a pasta caso ela não exista

# Inicializa a aplicação Flask
app = Flask(__name__)
CORS(app)  # Habilita CORS para permitir requisições de diferentes origens

# Rota para processar upload e incorporação de arquivos
@app.route('/embed', methods=['POST'])
def route_embed():
    if 'file' not in request.files:
        return jsonify({"error" : "No file part"}), 400 
        # Retorna erro se nenhum arquivo for enviado
    
    file = request.files['file']

    if file.filename == '':
        return jsonify({"error" : "No selected file"}), 400 
        # Retorna erro se nenhum arquivo for selecionado
    
    embedded = embed(file)  # Chama a função embed para processar o arquivo

    if embedded:
        return jsonify({"success" : "File added successfully"}), 200  
        # Retorna sucesso se a incorporação for bem-sucedida
    
    return jsonify({"error" : "File added unsuccessfully"}), 400  
    # Retorna erro se a incorporação falhar

# Rota antiga para processar consultas
@app.route('/query', methods=['POST'])
def route_query_old():
    data = request.get_json()  # Obtém os dados da requisição JSON
    response = query_old(data.get('message'))  # Chama a função query com a mensagem enviada

    if response:
        return jsonify({"answer": response}), 200  # Retorna a resposta com status 200
    else:
        return jsonify({"error": "Something went wrong"}), 400  # Retorna erro se a consulta falhar
    

# Rota NOVA para processar consultas (Utiliza MongoDB)
@app.route('/chats/new', methods=['POST'])
def route_new_chat():
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({"error": "Parâmetro 'user_id' é obrigatório"}), 400
    
    data = request.get_json()  # Obtém os dados da requisição JSON
    response = query_new_chat(user_id, data.get('message'))  # Chama a função query com a mensagem enviada

    if response:
        return jsonify({"answer": response}), 200  # Retorna a resposta com status 200
    else:
        return jsonify({"error": "Something went wrong"}), 400  # Retorna erro se a consulta falhar
        

@app.route('/chats/<chat_id>/add', methods=['POST'])
def route_resume_chat(chat_id):

    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({"error": "Parâmetro 'user_id' é obrigatório"}), 400
    
    data = request.get_json()  # Obtém os dados da requisição JSON
    message = data.get('message')

    response = continue_chat(user_id, chat_id, message)  # Chama a função query com a mensagem enviada

    if response:
        return jsonify({"answer": response}), 200  # Retorna a resposta com status 200
    else:
        return jsonify({"error": "Something went wrong"}), 400  # Retorna erro se a consulta falhar
    

@app.route('/chats', methods=['GET'])
def route_list_chats():
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({"error": "Parâmetro 'user_id' é obrigatório"}), 400
    
    return jsonify(list_last_chats(user_id))


@app.route('/chats/<chat_id>', methods=['GET'])
def get_chat(chat_id):
    # 1. Obter user_id (agora obrigatório)
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({"error": "Parâmetro 'user_id' é obrigatório"}), 400
    
    chat = get_chat_info(user_id, chat_id)

    if not chat:
        return jsonify({"error": "Conversa não encontrada"}), 404
    
    # 3. Retornar os dados 
    return jsonify(chat), 200


@app.route('/chats/<chat_id>/delete', methods=['DELETE'])
def delete_chat(chat_id):
    # 1. Obter user_id (agora obrigatório)
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({"error": "Parâmetro 'user_id' é obrigatório"}), 400
    
    # 2. Deletar conversa
    result = delete_conversation(user_id, chat_id)

    if result:
        return jsonify({"success": "Conversa deletada com sucesso"}), 200
    else:
        return jsonify({"error": "Erro ao deletar conversa"}), 500


# Inicia o servidor Flask quando o script for executado diretamente
if __name__ == "__main__":
    app.run()  # Executa o servidor na porta padrão 5000
