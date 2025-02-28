import os
from dotenv import load_dotenv  # Biblioteca para carregar variáveis de ambiente do arquivo .env

load_dotenv()  # Carrega as variáveis de ambiente

from flask import Flask, jsonify, request  # Importa módulos do Flask para criar a API
from flask_cors import CORS  # Importa CORS para permitir requisições de diferentes origens
from query import query  # Função importada para processar consultas
from embed import embed  # Função importada para processar a incorporação de arquivos

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

# Rota para processar consultas
@app.route('/query', methods=['POST'])
def route_query():
    data = request.get_json()  # Obtém os dados da requisição JSON
    response = query(data.get('message'))  # Chama a função query com a mensagem enviada

    if response:
        return jsonify({"answer": response}), 200  # Retorna a resposta com status 200
    else:
        return jsonify({"error": "Something went wrong"}), 400  # Retorna erro se a consulta falhar

# Inicia o servidor Flask quando o script for executado diretamente
if __name__ == "__main__":
    app.run()  # Executa o servidor na porta padrão 5000
