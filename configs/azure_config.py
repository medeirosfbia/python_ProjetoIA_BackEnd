import os
from pathlib import Path

from dotenv import load_dotenv
from azure.storage.queue import QueueClient
from azure.core.exceptions import ResourceExistsError

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
QUEUE_NAME = os.getenv("QUEUE_NAME")

queue_client = None

if AZURE_STORAGE_CONNECTION_STRING:
    queue_client = QueueClient.from_connection_string(
        conn_str=AZURE_STORAGE_CONNECTION_STRING,
        queue_name=QUEUE_NAME,
    )

    try:
        queue_client.create_queue()
    except ResourceExistsError:
        pass

    print(f"Azure Queue '{QUEUE_NAME}' pronta para publicar mensagens.")
else:
    print("Azure Queue desabilitada: AZURE_STORAGE_CONNECTION_STRING não configurada.")