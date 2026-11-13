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

    @patch("controllers.chat_controller.query_new_chat")
    def test_new_chat_rejects_unknown_model_before_creating_chat(self, query_new_chat):
        response = self.client.post(
            "/chats/new", json={"model": "llama3.2:3b", "message": "Hello"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "INVALID_CHAT_MODEL")
        query_new_chat.assert_not_called()

    @patch("controllers.chat_controller.continue_chat")
    def test_continue_accepts_legacy_model_and_rejects_unknown_one(self, continue_chat):
        response = self.client.post(
            "/chats/chat-1/add", json={"model": "unknown", "message": "Oi"}
        )
        self.assertEqual(response.status_code, 400)
        continue_chat.assert_not_called()

    @patch("controllers.chat_controller.continue_chat")
    def test_continue_requires_explicit_model_for_legacy_chat(self, continue_chat):
        from services.chat_service import ChatModelRequiredError

        continue_chat.side_effect = ChatModelRequiredError()
        response = self.client.post("/chats/chat-1/add", json={"message": "Oi"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["code"], "CHAT_MODEL_REQUIRED")

    @patch("controllers.chat_controller.continue_chat")
    def test_continue_rejects_different_persisted_tutor(self, continue_chat):
        from services.chat_service import ChatModelConflictError

        continue_chat.side_effect = ChatModelConflictError()
        response = self.client.post(
            "/chats/chat-1/add", json={"model": "qwen2-math", "message": "Oi"}
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["code"], "CHAT_MODEL_CONFLICT")

    @patch("controllers.chat_controller.associate_chat_model")
    def test_associate_legacy_chat_model(self, associate_chat_model):
        associate_chat_model.return_value = ({"chat_id": "chat-1", "model": "llama3"}, False)
        response = self.client.patch("/chats/chat-1/model", json={"model": "llama3"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"chat_id": "chat-1", "model": "llama3"})
        associate_chat_model.assert_called_once_with("user-1", "chat-1", "llama3")

    @patch("controllers.chat_controller.associate_chat_model")
    def test_associate_legacy_chat_model_does_not_expose_other_user(self, associate_chat_model):
        associate_chat_model.return_value = (None, False)
        response = self.client.patch("/chats/chat-2/model", json={"model": "llama3"})
        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    unittest.main()
