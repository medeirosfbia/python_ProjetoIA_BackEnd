import os
from datetime import datetime
from werkzeug.utils import secure_filename
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from get_vector_db import get_vector_db

# Obtém a pasta temporária da variável de ambiente
TEMP_FOLDER = os.getenv('TEMP_FOLDER')

# Função para verificar se o arquivo é permitido (somente PDFs)
def allowed_file(filename):
    has_dot = '.' in filename  # Verifica se há um ponto no nome do arquivo
    is_pdf = filename.rsplit('.', 1)[1].lower() in {'pdf'}  # Verifica se a extensão é PDF
    return has_dot and is_pdf

# Função para salvar o arquivo temporariamente
def save_file(file):
    ct = datetime.now()
    ts = ct.timestamp()  # Obtém o timestamp atual
    new_filename = str(ts) + "_" + secure_filename(file.filename)  # Gera um nome único para o arquivo
    file_path = os.path.join(TEMP_FOLDER, new_filename)  # Define o caminho para salvar o arquivo
    file.save(file_path)  # Salva o arquivo no diretório temporário
    return file_path

# Função para carregar e dividir os dados do arquivo PDF
def load_and_split_data(file_path):
    loader = UnstructuredPDFLoader(file_path=file_path)  # Carrega o arquivo PDF
    data = loader.load()  # Extrai o conteúdo do PDF
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=7500, chunk_overlap=100)  # Divide o texto em partes menores
    chunks = text_splitter.split_documents(data)  # Realiza a divisão do documento
    return chunks

# Função para processar e armazenar os embeddings do arquivo
def embed(file):
    if file.filename != '' and file and allowed_file(file.filename):  # Verifica se o arquivo é válido
        file_path = save_file(file)  # Salva o arquivo temporariamente
        chunks = load_and_split_data(file_path)  # Carrega e divide o arquivo
        db = get_vector_db()  # Obtém a instância do banco de vetores
        db.add_documents(chunks)  # Adiciona os documentos ao banco de dados vetorial
        os.remove(file_path)  # Remove o arquivo temporário após o processamento
    return True
