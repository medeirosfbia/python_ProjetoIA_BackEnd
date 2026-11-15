import json
import base64
from datetime import datetime, timezone
from configs.azure_config import notifications_queue_client

# Destinatário especial: todos os aparelhos cadastrados
TODOS_USUARIOS = "all"


def publicar_notificacao(tipo, titulo, corpo, destinatarios=TODOS_USUARIOS, dados=None):
    """Publica um evento para a Azure Function enviar o push via Expo.

    destinatarios é "all" ou uma lista de user_id (sub do JWT).
    """
    if notifications_queue_client is None:
        raise RuntimeError(
            "Azure Queue não configurada; notificação não publicada."
        )

    try:
        evento = {
            "type": tipo,
            "recipients": destinatarios,
            "title": titulo,
            "body": corpo,
            "data": dados or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        mensagem = base64.b64encode(
            json.dumps(evento, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        response = notifications_queue_client.send_message(mensagem)
        return response.id

    except Exception as e:
        print(f"Erro ao enviar notificação para a fila: {e}")
        raise
