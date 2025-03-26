import os
from pymongo import MongoClient, ASCENDING, DESCENDING

URL_CONNECTION_MONGODB = os.getenv('URL_CONNECTION_MONGODB')
DATABASE_NAME = os.getenv('DATABASE_NAME')
ASSISTANT_COLLECTION  = os.getenv('ASSISTANT_COLLECTION')


# Conexão com o MongoDB (local por padrão)
client = MongoClient(URL_CONNECTION_MONGODB)

# try:
#     client.admin.command('ping')
#     print("Conexão bem-sucedida com o MongoDB Atlas!")
# except Exception as e:
#     print(f"Erro ao conectar: {e}")


# Acesse um banco de dados e uma coleção
db = client[DATABASE_NAME]
collection = db[ASSISTANT_COLLECTION]

collection.create_index([
    ("user_id", ASCENDING),
    ("chat_id", ASCENDING)
], unique=True, name="user_chat_unique")

# Índice para listar conversas recentes
collection.create_index([
    ("user_id", ASCENDING),
    ("updated_at", DESCENDING)
], name="user_recent_chats")

