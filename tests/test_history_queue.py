import base64
import json
import unittest
from unittest.mock import patch

from models import history


class HistoryQueueTestCase(unittest.TestCase):
    @patch("models.history.publicar_mensagem_historico")
    @patch("models.history.collection")
    def test_update_chat_only_publishes_message(self, collection, publish_message):

        history.update_chat("user-1", "chat-1", "user", "Ola")

        publish_message.assert_called_once_with(
            "user-1", "chat-1", "user", "Ola"
        )
        collection.update_one.assert_not_called()

    @patch("messaging.queue_history_producer.queue_client")
    def test_producer_sends_base64_json_message(self, queue_client):
        queue_client.send_message.return_value.id = "message-1"

        message_id = history.publicar_mensagem_historico(
            "user-1", "chat-1", "assistant", "Resposta"
        )

        self.assertEqual(message_id, "message-1")
        encoded_message = queue_client.send_message.call_args.args[0]
        event = json.loads(base64.b64decode(encoded_message))
        self.assertEqual(event["chatId"], "chat-1")
        self.assertEqual(event["userId"], "user-1")
        self.assertEqual(event["role"], "assistant")
        self.assertEqual(event["content"], "Resposta")
        self.assertIn("timestamp", event)


if __name__ == "__main__":
    unittest.main()