import re
import unittest
from unittest.mock import patch

import app  # noqa: F401  carrega o .env antes dos models
from models import history


class CreateChatIdTestCase(unittest.TestCase):
    @patch("models.history.collection")
    def test_chats_created_in_same_second_get_different_ids(self, collection):
        ids = {history.create_chat("ana", "Oi") for _ in range(50)}

        self.assertEqual(len(ids), 50)
        for chat_id in ids:
            self.assertRegex(chat_id, re.compile(r"^chat_\d{8}_\d{6}_[0-9a-f]{8}$"))


if __name__ == "__main__":
    unittest.main()
