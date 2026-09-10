import json
import base64
from datetime import datetime, timezone
from configs.azure_config import queue_client


def publicar_mensagem_historico(user_id, chat_id, role, content):
    if queue_client is None:
        raise RuntimeError(
            "Azure Queue não configurada; evento de histórico não publicado."
        )

    try:
        evento = {
            "chatId": chat_id,
            "userId": user_id,
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        mensagem = base64.b64encode(
            json.dumps(evento, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        response = queue_client.send_message(mensagem)
        return response.id

    except Exception as e:
        print(f"Erro ao enviar mensagem para a fila: {e}")
        raise