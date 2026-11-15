import base64
import json
import unittest
from unittest.mock import patch

from azure.core.exceptions import AzureError

import app as app_module
from messaging import queue_notification_producer
from services import exam_service, material_service, notification_service
from services.notification_service import NotificationValidationError

TOKEN = "ExponentPushToken[abc123_-XYZ]"


class NotificationEndpointsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_module.app.config.update(TESTING=True)

    def setUp(self):
        self.auth_patcher = patch.object(
            app_module, "authenticate_request", return_value=None
        )
        self.auth_patcher.start()
        self.user_patcher = patch(
            "controllers.notification_controller.authenticated_user_id",
            return_value="user-1",
        )
        self.user_patcher.start()
        self.admin_patcher = patch(
            "controllers.notification_controller.is_admin", return_value=False
        )
        self.is_admin = self.admin_patcher.start()
        self.client = app_module.app.test_client()

    def tearDown(self):
        self.admin_patcher.stop()
        self.user_patcher.stop()
        self.auth_patcher.stop()

    @patch("services.notification_service.push_token_model")
    def test_user_registers_token(self, push_token_model):
        response = self.client.post(
            "/notifications/tokens", json={"token": TOKEN, "platform": "android"}
        )

        self.assertEqual(response.status_code, 201)
        push_token_model.save_token.assert_called_once_with("user-1", TOKEN, "android")

    @patch("services.notification_service.push_token_model")
    def test_register_rejects_invalid_token_and_platform(self, push_token_model):
        response = self.client.post(
            "/notifications/tokens", json={"token": "abc", "platform": "web"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.get_json()["detalhes"]), 2)
        push_token_model.save_token.assert_not_called()

    @patch("services.notification_service.push_token_model")
    def test_register_rejects_non_object_body(self, push_token_model):
        response = self.client.post("/notifications/tokens", json=[TOKEN])

        self.assertEqual(response.status_code, 400)
        push_token_model.save_token.assert_not_called()

    @patch("services.notification_service.push_token_model")
    def test_user_unregisters_own_token(self, push_token_model):
        push_token_model.delete_token.return_value = True

        response = self.client.delete("/notifications/tokens", json={"token": TOKEN})

        self.assertEqual(response.status_code, 200)
        push_token_model.delete_token.assert_called_once_with("user-1", TOKEN)

    @patch("services.notification_service.push_token_model")
    def test_unregister_unknown_token_returns_not_found(self, push_token_model):
        push_token_model.delete_token.return_value = False

        response = self.client.delete("/notifications/tokens", json={"token": TOKEN})

        self.assertEqual(response.status_code, 404)

    @patch("services.notification_service.publicar_notificacao")
    def test_student_cannot_send(self, publicar):
        response = self.client.post(
            "/notifications/send", json={"title": "Oi", "body": "Teste"}
        )

        self.assertEqual(response.status_code, 403)
        publicar.assert_not_called()

    @patch("services.notification_service.publicar_notificacao", return_value="msg-1")
    def test_admin_sends_to_all_by_default(self, publicar):
        self.is_admin.return_value = True

        response = self.client.post(
            "/notifications/send", json={"title": " Oi ", "body": "Teste"}
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.get_json(), {"messageId": "msg-1"})
        publicar.assert_called_once_with(
            "custom", titulo="Oi", corpo="Teste", destinatarios="all", dados={}
        )

    @patch("services.notification_service.publicar_notificacao")
    def test_admin_send_validation_error(self, publicar):
        self.is_admin.return_value = True

        response = self.client.post(
            "/notifications/send",
            json={"title": "", "body": "x" * 501, "recipients": [], "data": "x"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.get_json()["detalhes"]), 4)
        publicar.assert_not_called()

    @patch(
        "services.notification_service.publicar_notificacao",
        side_effect=AzureError("fora do ar"),
    )
    def test_admin_send_queue_unavailable(self, publicar):
        self.is_admin.return_value = True

        response = self.client.post(
            "/notifications/send", json={"title": "Oi", "body": "Teste"}
        )

        self.assertEqual(response.status_code, 503)


class NotificationServiceTestCase(unittest.TestCase):
    def test_send_payload_deduplicates_recipients(self):
        campos = notification_service.validate_send_payload(
            {"title": "Oi", "body": "Teste", "recipients": ["b", "a", " a "]}
        )

        self.assertEqual(campos["destinatarios"], ["a", "b"])

    def test_accepts_both_expo_token_prefixes(self):
        for token in (TOKEN, "ExpoPushToken[abc]"):
            errors = []
            notification_service._validate_token({"token": token}, errors)
            self.assertEqual(errors, [])

    def test_rejects_token_with_extra_content(self):
        errors = []
        notification_service._validate_token({"token": TOKEN + "x"}, errors)
        self.assertEqual(len(errors), 1)

    @patch("services.notification_service.publicar_notificacao", side_effect=RuntimeError)
    def test_event_notification_never_raises(self, publicar):
        notification_service.notify_exam_published({"_id": "prova-1", "titulo": "Simulado"})

        publicar.assert_called_once()

    @patch("services.notification_service.publicar_notificacao")
    def test_exam_notification_content(self, publicar):
        notification_service.notify_exam_published({
            "_id": "prova-1",
            "titulo": "Simulado",
            "contexto": {"assunto_materia": "Matemática"},
        })

        publicar.assert_called_once_with(
            "exam_published",
            "Nova prova disponível",
            "Simulado (Matemática)",
            dados={"examId": "prova-1"},
        )

    @patch("services.notification_service.publicar_notificacao")
    def test_malformed_event_never_raises(self, publicar):
        notification_service.notify_material_created({"caminho": "x/y.pdf"})

        publicar.assert_not_called()

    @patch("messaging.queue_notification_producer.notifications_queue_client")
    def test_producer_sends_base64_json_message(self, queue_client):
        queue_client.send_message.return_value.id = "message-1"

        message_id = queue_notification_producer.publicar_notificacao(
            "custom", "Título", "Corpo", ["user-1"], {"examId": "prova-1"}
        )

        self.assertEqual(message_id, "message-1")
        encoded_message = queue_client.send_message.call_args.args[0]
        event = json.loads(base64.b64decode(encoded_message))
        self.assertEqual(event["type"], "custom")
        self.assertEqual(event["recipients"], ["user-1"])
        self.assertEqual(event["title"], "Título")
        self.assertEqual(event["body"], "Corpo")
        self.assertEqual(event["data"], {"examId": "prova-1"})
        self.assertIn("timestamp", event)

    @patch("messaging.queue_notification_producer.notifications_queue_client", None)
    def test_producer_requires_queue(self):
        with self.assertRaises(RuntimeError):
            queue_notification_producer.publicar_notificacao("custom", "T", "C")

    def test_invalid_body_raises_validation_error(self):
        with self.assertRaises(NotificationValidationError):
            notification_service.register_token("user-1", None)


class NotificationTriggersTestCase(unittest.TestCase):
    CAMPOS = {"titulo": "Simulado", "status": "APROVADO", "contexto": {}}

    @patch("services.exam_service.notify_exam_published")
    @patch("services.exam_service.exam_model")
    @patch("services.exam_service.validate_exam_payload")
    def test_creating_published_exam_notifies(self, validate, exam_model, notify):
        validate.return_value = self.CAMPOS

        exam = exam_service.create_exam("admin", {})

        notify.assert_called_once_with(exam)

    @patch("services.exam_service.notify_exam_published")
    @patch("services.exam_service.exam_model")
    @patch("services.exam_service.validate_exam_payload")
    def test_creating_draft_does_not_notify(self, validate, exam_model, notify):
        validate.return_value = {**self.CAMPOS, "status": "RASCUNHO"}

        exam_service.create_exam("admin", {})

        notify.assert_not_called()

    @patch("services.exam_service.notify_exam_published")
    @patch("services.exam_service.exam_model")
    @patch("services.exam_service.validate_exam_payload")
    def test_publishing_draft_notifies_once(self, validate, exam_model, notify):
        validate.return_value = self.CAMPOS
        exam_model.replace_exam.return_value = True

        exam_model.get_exam.return_value = {"_id": "prova-1", "status": "RASCUNHO", "contexto": {}}
        exam_service.update_exam("prova-1", "admin", {})
        exam_model.get_exam.return_value = {"_id": "prova-1", "status": "APROVADO", "contexto": {}}
        exam_service.update_exam("prova-1", "admin", {})

        notify.assert_called_once()

    @patch("services.material_service.notify_material_created")
    @patch("services.material_service.material_model")
    @patch("services.material_service._validate_file")
    def test_creating_material_notifies(self, validate_file, material_model, notify):
        validate_file.return_value = (None, 3, "application/pdf")
        material_model.upload_material.return_value = {"conteudo": "matematica", "nome": "aula.pdf"}

        class Arquivo:
            filename = "aula.pdf"

        material = material_service.create_material("matematica", Arquivo(), "admin")

        notify.assert_called_once_with(material)


if __name__ == "__main__":
    unittest.main()
