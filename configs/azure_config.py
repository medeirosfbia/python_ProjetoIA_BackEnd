import os
from pathlib import Path

from dotenv import load_dotenv
from azure.storage.queue import QueueClient
from azure.core.exceptions import ResourceExistsError

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
QUEUE_NAME = os.getenv("QUEUE_NAME")
NOTIFICATIONS_QUEUE_NAME = os.getenv("NOTIFICATIONS_QUEUE_NAME", "aprovia-notifications")


def _build_queue_client(queue_name):
    client = QueueClient.from_connection_string(
        conn_str=AZURE_STORAGE_CONNECTION_STRING,
        queue_name=queue_name,
    )

    try:
        client.create_queue()
    except ResourceExistsError:
        pass

    print(f"Azure Queue '{queue_name}' pronta para publicar mensagens.")
    return client


queue_client = None
notifications_queue_client = None

if AZURE_STORAGE_CONNECTION_STRING:
    queue_client = _build_queue_client(QUEUE_NAME)
    notifications_queue_client = _build_queue_client(NOTIFICATIONS_QUEUE_NAME)
else:
    print("Azure Queue desabilitada: AZURE_STORAGE_CONNECTION_STRING não configurada.")
