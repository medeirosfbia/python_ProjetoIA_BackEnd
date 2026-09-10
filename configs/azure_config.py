import os
from dotenv import load_dotenv
from azure.storage.queue import QueueClient

load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
QUEUE_NAME = "aprova-chat-history"

if not AZURE_STORAGE_CONNECTION_STRING:
    raise ValueError("A variável de ambiente AZURE_STORAGE_CONNECTION_STRING não foi configurada.")

# Inicializa o cliente da fila do Azure
queue_client = QueueClient.from_connection_string(
    conn_str=AZURE_STORAGE_CONNECTION_STRING, 
    queue_name=QUEUE_NAME
)

# Garante que a fila existe no Azure Storage
try:
    queue_client.create_queue()
    print(f"Fila '{QUEUE_NAME}' criada com sucesso no Azure Queue Storage.")
except Exception:
    # Caso a fila já exista, o Azure lança um erro que podemos ignorar
    print(f"Fila '{QUEUE_NAME}' pronta para uso.")