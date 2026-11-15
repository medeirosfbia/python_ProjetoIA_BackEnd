import unittest
from datetime import datetime
from unittest.mock import patch

import app  # noqa: F401  carrega o .env antes dos models
from services import chat_service
from services.chat_service import (
    MENSAGEM_ERRO,
    ChatNotFoundError,
    InvalidModelError,
    continue_chat,
    query_new_chat,
)


def chunks(*partes):
    return iter([{"message": {"content": parte}} for parte in partes])


@patch("services.chat_service.update_chat")
@patch("services.chat_service.create_chat", return_value="chat-1")
@patch("services.chat_service.ollama")
class NewChatTestCase(unittest.TestCase):
    def test_english_chat_uses_llama3_and_english_prompt(self, ollama, create_chat, update_chat):
        # Bug corrigido: "llama3" (id enviado pelos apps) quebrava com UnboundLocalError
        ollama.chat.return_value = chunks("Hi")

        response = query_new_chat("ana", "llama3", "hello")
        "".join(response["resposta_stream"])

        kwargs = ollama.chat.call_args.kwargs
        self.assertEqual(kwargs["model"], "llama3")
        self.assertEqual(kwargs["messages"][0]["content"], chat_service.english_context)
        create_chat.assert_called_once_with("ana", title="Hello...", model="llama3")

    def test_math_chat_uses_math_prompt(self, ollama, create_chat, update_chat):
        ollama.chat.return_value = chunks("1")

        "".join(query_new_chat("ana", "qwen2-math", "2+2")["resposta_stream"])

        kwargs = ollama.chat.call_args.kwargs
        self.assertEqual(kwargs["model"], "qwen2-math")
        self.assertEqual(kwargs["messages"][0]["content"], chat_service.math_context)

    def test_invalid_model_fails_before_creating_chat(self, ollama, create_chat, update_chat):
        for invalido in ("llama3.2:3b", "gpt-qualquer", None):
            with self.assertRaises(InvalidModelError):
                query_new_chat("ana", invalido, "oi")
        create_chat.assert_not_called()
        ollama.chat.assert_not_called()

    def test_saves_complete_response(self, ollama, create_chat, update_chat):
        ollama.chat.return_value = chunks("Olá", ", tudo bem?")

        resposta = "".join(query_new_chat("ana", "llama3", "oi")["resposta_stream"])

        self.assertEqual(resposta, "Olá, tudo bem?")
        update_chat.assert_any_call("ana", "chat-1", "user", "oi")
        update_chat.assert_called_with("ana", "chat-1", "assistant", "Olá, tudo bem?")

    def test_model_error_is_streamed_but_not_saved(self, ollama, create_chat, update_chat):
        def falha():
            yield {"message": {"content": "Parcial"}}
            raise ConnectionError("ollama fora")
        ollama.chat.return_value = falha()

        with self.assertLogs("services.chat_service", level="ERROR"):
            resposta = "".join(query_new_chat("ana", "llama3", "oi")["resposta_stream"])

        self.assertEqual(resposta, "Parcial" + MENSAGEM_ERRO)
        # Só a mensagem do usuário foi gravada
        update_chat.assert_called_once_with("ana", "chat-1", "user", "oi")


@patch("services.chat_service.update_chat")
@patch("services.chat_service.get_chat_messages")
@patch("services.chat_service.ollama")
class ContinueChatTestCase(unittest.TestCase):
    def test_uses_tutor_saved_in_chat(self, ollama, get_chat_messages, update_chat):
        get_chat_messages.return_value = {"model": "qwen2-math", "messages": []}
        ollama.chat.return_value = chunks("ok")

        "".join(continue_chat("ana", "chat-1", "llama3", "e agora?")["resposta_stream"])

        self.assertEqual(ollama.chat.call_args.kwargs["model"], "qwen2-math")

    def test_old_chat_without_tutor_uses_requested_model(self, ollama, get_chat_messages, update_chat):
        get_chat_messages.return_value = {"messages": []}
        ollama.chat.return_value = chunks("ok")

        "".join(continue_chat("ana", "chat-1", "llama3", "hi")["resposta_stream"])

        self.assertEqual(ollama.chat.call_args.kwargs["model"], "llama3")

    def test_old_chat_without_tutor_requires_valid_model(self, ollama, get_chat_messages, update_chat):
        get_chat_messages.return_value = {"messages": []}

        with self.assertRaises(InvalidModelError):
            continue_chat("ana", "chat-1", None, "hi")
        update_chat.assert_not_called()

    def test_missing_chat_raises_not_found(self, ollama, get_chat_messages, update_chat):
        get_chat_messages.side_effect = ValueError("Conversa não encontrada")

        with self.assertRaises(ChatNotFoundError):
            continue_chat("ana", "chat-x", "llama3", "hi")

    def test_sends_last_messages_without_extra_fields(self, ollama, get_chat_messages, update_chat):
        historico = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}", "timestamp": datetime(2026, 1, 1)}
            for i in range(12)
        ]
        get_chat_messages.return_value = {"model": "llama3", "messages": historico}
        ollama.chat.return_value = chunks("ok")

        "".join(continue_chat("ana", "chat-1", None, "nova")["resposta_stream"])

        messages = ollama.chat.call_args.kwargs["messages"]
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual([m["content"] for m in messages[1:-1]], [f"m{i}" for i in range(2, 12)])
        self.assertTrue(all(set(m) == {"role", "content"} for m in messages))
        self.assertEqual(messages[-1], {"role": "user", "content": "nova"})


if __name__ == "__main__":
    unittest.main()
