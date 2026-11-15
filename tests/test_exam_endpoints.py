import unittest
from unittest.mock import patch

from flask import g

import app as app_module
from services.auth_service import is_admin
from services.exam_service import ExamConflictError, ExamValidationError


class ExamEndpointsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_module.app.config.update(TESTING=True)

    def setUp(self):
        self.auth_patcher = patch.object(
            app_module, "authenticate_request", return_value=None
        )
        self.auth_patcher.start()
        self.user_patcher = patch(
            "controllers.exam_controller.authenticated_user_id",
            return_value="user-1",
        )
        self.user_patcher.start()
        self.admin_patcher = patch(
            "controllers.exam_controller.is_admin", return_value=False
        )
        self.is_admin = self.admin_patcher.start()
        self.client = app_module.app.test_client()

    def tearDown(self):
        self.admin_patcher.stop()
        self.user_patcher.stop()
        self.auth_patcher.stop()

    def as_admin(self):
        self.is_admin.return_value = True

    @patch("controllers.exam_controller.list_exams")
    def test_list_exams_passes_role_and_filters(self, list_exams):
        list_exams.return_value = [{"_id": "prova-1", "titulo": "Simulado"}]

        response = self.client.get("/exams?assunto=Matemática")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), list_exams.return_value)
        list_exams.assert_called_once_with(False, assunto="Matemática", status=None)

    @patch("controllers.exam_controller.get_exam", return_value=None)
    def test_get_exam_returns_not_found(self, get_exam):
        response = self.client.get("/exams/missing")

        self.assertEqual(response.status_code, 404)
        get_exam.assert_called_once_with("missing", False)

    @patch("controllers.exam_controller.create_exam")
    def test_student_cannot_create_exam(self, create_exam):
        response = self.client.post("/exams", json={"titulo": "x"})

        self.assertEqual(response.status_code, 403)
        create_exam.assert_not_called()

    @patch("controllers.exam_controller.update_exam")
    def test_student_cannot_update_exam(self, update_exam):
        response = self.client.put("/exams/prova-1", json={"titulo": "x"})

        self.assertEqual(response.status_code, 403)
        update_exam.assert_not_called()

    @patch("controllers.exam_controller.delete_exam")
    def test_student_cannot_delete_exam(self, delete_exam):
        response = self.client.delete("/exams/prova-1")

        self.assertEqual(response.status_code, 403)
        delete_exam.assert_not_called()

    @patch("controllers.exam_controller.list_exam_answers")
    def test_student_cannot_list_all_answers(self, list_exam_answers):
        response = self.client.get("/exams/prova-1/answers/all")

        self.assertEqual(response.status_code, 403)
        list_exam_answers.assert_not_called()

    @patch("controllers.exam_controller.create_exam")
    def test_admin_creates_exam(self, create_exam):
        self.as_admin()
        create_exam.return_value = {"_id": "prova-1", "titulo": "Simulado"}

        response = self.client.post("/exams", json={"titulo": "Simulado"})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json(), create_exam.return_value)
        create_exam.assert_called_once_with("user-1", {"titulo": "Simulado"})

    @patch(
        "controllers.exam_controller.create_exam",
        side_effect=ExamValidationError(["titulo é obrigatório"]),
    )
    def test_admin_create_returns_validation_details(self, create_exam):
        self.as_admin()

        response = self.client.post("/exams", json={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["detalhes"], ["titulo é obrigatório"])

    @patch("controllers.exam_controller.update_exam", return_value=None)
    def test_admin_update_missing_exam_returns_not_found(self, update_exam):
        self.as_admin()

        response = self.client.put("/exams/missing", json={"titulo": "x"})

        self.assertEqual(response.status_code, 404)
        update_exam.assert_called_once_with("missing", "user-1", {"titulo": "x"})

    @patch("controllers.exam_controller.delete_exam", return_value=True)
    def test_admin_deletes_exam(self, delete_exam):
        self.as_admin()

        response = self.client.delete("/exams/prova-1")

        self.assertEqual(response.status_code, 200)
        delete_exam.assert_called_once_with("prova-1")

    @patch("controllers.exam_controller.submit_answers")
    def test_submit_answers_returns_created(self, submit_answers):
        submit_answers.return_value = {"_id": "resp-1", "resultado": {"nota_obtida": 8.0}}
        body = {"respostas": [{"id_questao": "q1", "resposta": "op_b"}]}

        response = self.client.post("/exams/prova-1/answers", json=body)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json(), submit_answers.return_value)
        submit_answers.assert_called_once_with("prova-1", "user-1", False, body)

    @patch(
        "controllers.exam_controller.submit_answers",
        side_effect=ExamConflictError("Esta prova não permite refazer"),
    )
    def test_submit_answers_conflict(self, submit_answers):
        response = self.client.post("/exams/prova-1/answers", json={"respostas": []})

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"], "Esta prova não permite refazer")

    @patch("controllers.exam_controller.list_user_answers", return_value=[])
    def test_answers_history_is_not_routed_as_exam_id(self, list_user_answers):
        response = self.client.get("/exams/answers")

        self.assertEqual(response.status_code, 200)
        list_user_answers.assert_called_once_with("user-1")

    @patch("controllers.exam_controller.list_user_answers", return_value=[])
    def test_my_answers_for_exam(self, list_user_answers):
        response = self.client.get("/exams/prova-1/answers")

        self.assertEqual(response.status_code, 200)
        list_user_answers.assert_called_once_with("user-1", "prova-1")


class IsAdminTestCase(unittest.TestCase):
    def check(self, claims, admin_users=""):
        with app_module.app.test_request_context(), patch.dict(
            "os.environ", {"ADMIN_USERS": admin_users}
        ):
            g.user_id = "user-1"
            g.jwt_claims = claims
            return is_admin()

    def test_role_claim(self):
        self.assertTrue(self.check({"role": "ADMIN"}))
        self.assertTrue(self.check({"roles": ["USER", "ROLE_ADMIN"]}))
        self.assertTrue(self.check({"roles": ["admin"]}))

    def test_admin_users_env(self):
        self.assertTrue(self.check({}, admin_users="outro, user-1"))

    def test_regular_user(self):
        self.assertFalse(self.check({}))
        self.assertFalse(self.check({"roles": ["USER"]}, admin_users="outro"))
        self.assertFalse(self.check({"roles": {"ADMIN": True}}))


if __name__ == "__main__":
    unittest.main()
