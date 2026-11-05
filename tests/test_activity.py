import base64
import os
import time
import unittest
from unittest.mock import patch

import jwt

import app as app_module
from services import activity_service


@patch("services.activity_service.user_activity_model")
class ActivityServiceTestCase(unittest.TestCase):
    def setUp(self):
        activity_service._cache_day = None
        activity_service._cache_users = set()

    @patch("services.activity_service.local_today", return_value="2026-11-04")
    def test_marks_user_once_per_day(self, local_today, model):
        activity_service.record_activity("ana")
        activity_service.record_activity("ana")
        activity_service.record_activity("bruno")

        self.assertEqual(model.mark_active.call_count, 2)
        model.mark_active.assert_any_call("ana", "2026-11-04")
        model.mark_active.assert_any_call("bruno", "2026-11-04")

    @patch("services.activity_service.local_today")
    def test_marks_again_on_next_day(self, local_today, model):
        local_today.return_value = "2026-11-04"
        activity_service.record_activity("ana")
        local_today.return_value = "2026-11-05"
        activity_service.record_activity("ana")

        self.assertEqual(model.mark_active.call_count, 2)
        model.mark_active.assert_called_with("ana", "2026-11-05")

    @patch("services.activity_service.local_today", return_value="2026-11-04")
    def test_database_failure_does_not_raise_and_retries(self, local_today, model):
        model.mark_active.side_effect = [RuntimeError("mongo fora"), None]

        activity_service.record_activity("ana")
        activity_service.record_activity("ana")

        self.assertEqual(model.mark_active.call_count, 2)

    def test_today_uses_configured_timezone(self, model):
        # 02:00 UTC ainda é o dia anterior em São Paulo (UTC-3)
        with patch("services.activity_service.datetime") as fake_datetime:
            from datetime import datetime, timezone
            utc = datetime(2026, 11, 5, 2, 0, tzinfo=timezone.utc)
            fake_datetime.now.side_effect = lambda tz: utc.astimezone(tz)

            self.assertEqual(activity_service.local_today(), "2026-11-04")


class AuthenticatedRequestRecordsActivityTestCase(unittest.TestCase):
    SECRET = base64.b64encode(b"x" * 32).decode()

    def token(self, sub="ana"):
        return jwt.encode(
            {"sub": sub, "exp": int(time.time()) + 60},
            base64.b64decode(self.SECRET),
            algorithm="HS256",
        )

    @patch.dict(os.environ, {"JWT_SECRET_B64": SECRET})
    @patch("services.auth_service.record_activity")
    @patch("controllers.notification_controller.unregister_token", return_value=True)
    def test_valid_token_records_activity(self, unregister, record_activity):
        client = app_module.app.test_client()

        response = client.delete(
            "/notifications/tokens",
            json={"token": "ExponentPushToken[abc]"},
            headers={"Authorization": f"Bearer {self.token()}"},
        )

        self.assertEqual(response.status_code, 200)
        record_activity.assert_called_once_with("ana")

    @patch.dict(os.environ, {"JWT_SECRET_B64": SECRET})
    @patch("services.auth_service.record_activity")
    def test_invalid_token_does_not_record_activity(self, record_activity):
        client = app_module.app.test_client()

        response = client.get("/chats", headers={"Authorization": "Bearer invalido"})

        self.assertEqual(response.status_code, 401)
        record_activity.assert_not_called()


if __name__ == "__main__":
    unittest.main()
