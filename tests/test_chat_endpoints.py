import unittest
from unittest.mock import patch

import app as app_module


class ChatEndpointsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_module.app.config.update(TESTING=True)

    def setUp(self):
        self.auth_patcher = patch.object(
            app_module, "authenticate_request", return_value=None
        )
        self.auth_patcher.start()
        self.user_patcher = patch(
            "controllers.chat_controller.authenticated_user_id",
            return_value="user-1",
        )
        self.user_patcher.start()
        self.client = app_module.app.test_client()

    def tearDown(self):
        self.user_patcher.stop()
        self.auth_patcher.stop()

    @patch("controllers.chat_controller.query_new_chat")
    def test_new_chat_returns_stream_and_chat_id(self, query_new_chat):
        query_new_chat.return_value = {
            "chat_id": "chat-1",
            "resposta_stream": iter(["primeiro", " segundo"]),
        }

        response = self.client.post(
            "/chats/new",
            json={"model": "llama3", "message": "Hello"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Chat-ID"], "chat-1")
        self.assertEqual(response.data, b"primeiro segundo")
        query_new_chat.assert_called_once_with("user-1", "llama3", "Hello")

    @patch("controllers.chat_controller.continue_chat")
    def test_continue_chat_returns_stream_and_chat_id(self, continue_chat):
        continue_chat.return_value = {
            "chat_id": "chat-1",
            "resposta_stream": iter(["continuacao"]),
        }

        response = self.client.post(
            "/chats/chat-1/add",
            json={"model": "qwen2-math", "message": "2 + 2"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Chat-ID"], "chat-1")
        self.assertEqual(response.data, b"continuacao")
        continue_chat.assert_called_once_with(
            "user-1", "chat-1", "qwen2-math", "2 + 2"
        )

    @patch("controllers.chat_controller.list_last_chats")
    def test_list_chats_returns_json(self, list_last_chats):
        list_last_chats.return_value = [
            {"chat_id": "chat-1", "title": "Hello"}
        ]

        response = self.client.get("/chats")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), list_last_chats.return_value)
        list_last_chats.assert_called_once_with("user-1")

    @patch("controllers.chat_controller.get_chat_info")
    def test_get_chat_returns_chat(self, get_chat_info):
        get_chat_info.return_value = {
            "chat_id": "chat-1",
            "title": "Hello",
            "messages": [],
        }

        response = self.client.get("/chats/chat-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), get_chat_info.return_value)
        get_chat_info.assert_called_once_with("user-1", "chat-1")

    @patch("controllers.chat_controller.get_chat_info", return_value=None)
    def test_get_chat_returns_not_found(self, get_chat_info):
        response = self.client.get("/chats/missing")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"], "Conversa não encontrada")
        get_chat_info.assert_called_once_with("user-1", "missing")

    @patch("controllers.chat_controller.delete_conversation", return_value=True)
    def test_delete_chat_returns_success(self, delete_conversation):
        response = self.client.delete("/chats/chat-1/delete")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"success": "Conversa deletada com sucesso"},
        )
        delete_conversation.assert_called_once_with("user-1", "chat-1")

    @patch("controllers.chat_controller.delete_conversation", return_value=False)
    def test_delete_chat_returns_error_when_chat_is_not_deleted(
        self, delete_conversation
    ):
        response = self.client.delete("/chats/chat-1/delete")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"], "Erro ao deletar conversa")
        delete_conversation.assert_called_once_with("user-1", "chat-1")

    @patch("controllers.chat_controller.query_new_chat")
    def test_new_chat_rejects_missing_payload_fields(self, query_new_chat):
        response = self.client.post("/chats/new", json={"model": "llama3"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"],
            "model e message são obrigatórios",
        )
        query_new_chat.assert_not_called()

if __name__ == "__main__":
    unittest.main()
