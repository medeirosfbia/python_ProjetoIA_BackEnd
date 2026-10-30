import io
import unittest
from unittest.mock import MagicMock, patch

import app as app_module
from models.material import MaterialStorageUnavailable
from services import material_service
from services.material_service import MaterialConflictError, MaterialValidationError


def pdf_upload(nome="aula.pdf", conteudo=b"%PDF-1.4 teste"):
    return {"arquivo": (io.BytesIO(conteudo), nome)}


class MaterialEndpointsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_module.app.config.update(TESTING=True)

    def setUp(self):
        self.auth_patcher = patch.object(
            app_module, "authenticate_request", return_value=None
        )
        self.auth_patcher.start()
        self.user_patcher = patch(
            "controllers.material_controller.authenticated_user_id",
            return_value="user-1",
        )
        self.user_patcher.start()
        self.admin_patcher = patch(
            "controllers.material_controller.is_admin", return_value=False
        )
        self.is_admin = self.admin_patcher.start()
        self.client = app_module.app.test_client()

    def tearDown(self):
        self.admin_patcher.stop()
        self.user_patcher.stop()
        self.auth_patcher.stop()

    def as_admin(self):
        self.is_admin.return_value = True

    @patch("controllers.material_controller.list_folders", return_value=["matematica"])
    def test_user_lists_folders(self, list_folders):
        response = self.client.get("/materials/folders")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), ["matematica"])

    @patch("controllers.material_controller.list_materials", return_value=[])
    def test_user_lists_materials_by_folder(self, list_materials):
        response = self.client.get("/materials?conteudo=Matemática")

        self.assertEqual(response.status_code, 200)
        list_materials.assert_called_once_with("Matemática")

    @patch("controllers.material_controller.get_material", return_value=None)
    def test_get_missing_material(self, get_material):
        response = self.client.get("/materials/matematica/aula.pdf")

        self.assertEqual(response.status_code, 404)
        get_material.assert_called_once_with("matematica", "aula.pdf")

    @patch("controllers.material_controller.download_material")
    def test_user_downloads_material(self, download_material):
        downloader = MagicMock()
        downloader.name = "matematica/aula.pdf"
        downloader.size = 3
        downloader.chunks.return_value = iter([b"abc"])
        downloader.properties.content_settings.content_type = "application/pdf"
        download_material.return_value = downloader

        response = self.client.get("/materials/matematica/aula.pdf/download?download=1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"abc")
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertTrue(response.headers["Content-Disposition"].startswith("attachment"))

    @patch(
        "controllers.material_controller.list_folders",
        side_effect=MaterialStorageUnavailable("sem conexão"),
    )
    def test_storage_not_configured(self, list_folders):
        response = self.client.get("/materials/folders")

        self.assertEqual(response.status_code, 503)

    @patch("controllers.material_controller.create_material")
    def test_student_cannot_upload(self, create_material):
        response = self.client.post("/materials/matematica", data=pdf_upload())

        self.assertEqual(response.status_code, 403)
        create_material.assert_not_called()

    @patch("controllers.material_controller.update_material")
    def test_student_cannot_update(self, update_material):
        response = self.client.put("/materials/matematica/aula.pdf", data=pdf_upload())

        self.assertEqual(response.status_code, 403)
        update_material.assert_not_called()

    @patch("controllers.material_controller.delete_material")
    def test_student_cannot_delete(self, delete_material):
        response = self.client.delete("/materials/matematica/aula.pdf")

        self.assertEqual(response.status_code, 403)
        delete_material.assert_not_called()

    @patch("controllers.material_controller.create_material")
    def test_admin_uploads_material(self, create_material):
        self.as_admin()
        create_material.return_value = {"caminho": "matematica/aula.pdf"}

        response = self.client.post("/materials/matematica", data=pdf_upload())

        self.assertEqual(response.status_code, 201)
        conteudo, arquivo, user_id = create_material.call_args.args
        self.assertEqual((conteudo, arquivo.filename, user_id), ("matematica", "aula.pdf", "user-1"))

    @patch(
        "controllers.material_controller.create_material",
        side_effect=MaterialConflictError("Já existe"),
    )
    def test_admin_upload_conflict(self, create_material):
        self.as_admin()

        response = self.client.post("/materials/matematica", data=pdf_upload())

        self.assertEqual(response.status_code, 409)

    @patch(
        "controllers.material_controller.create_material",
        side_effect=MaterialValidationError(["extensão .exe não permitida"]),
    )
    def test_admin_upload_validation_error(self, create_material):
        self.as_admin()

        response = self.client.post("/materials/matematica", data=pdf_upload("x.exe"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["detalhes"], ["extensão .exe não permitida"])

    @patch("controllers.material_controller.update_material", return_value=None)
    def test_admin_update_missing_material(self, update_material):
        self.as_admin()

        response = self.client.put("/materials/matematica/aula.pdf", data=pdf_upload())

        self.assertEqual(response.status_code, 404)

    @patch("controllers.material_controller.delete_material", return_value=True)
    def test_admin_deletes_material(self, delete_material):
        self.as_admin()

        response = self.client.delete("/materials/matematica/aula.pdf")

        self.assertEqual(response.status_code, 200)
        delete_material.assert_called_once_with("matematica", "aula.pdf")


class MaterialServiceTestCase(unittest.TestCase):
    def upload(self, nome="aula.pdf", conteudo=b"%PDF"):
        arquivo = MagicMock()
        arquivo.filename = nome
        arquivo.stream = io.BytesIO(conteudo)
        return arquivo

    def test_normalize_conteudo(self):
        self.assertEqual(material_service.normalize_conteudo("Matemática Básica"), "matematica-basica")
        self.assertEqual(material_service.normalize_conteudo("ingles"), "ingles")
        for invalido in ("", "../segredo", "a/b", "-x", None):
            with self.assertRaises(MaterialValidationError):
                material_service.normalize_conteudo(invalido)

    @patch("services.material_service.material_model")
    def test_create_builds_path_and_content_type(self, model):
        model.upload_material.return_value = {"caminho": "matematica/Funcao_1o_grau.pdf"}

        material_service.create_material("Matemática", self.upload("Função 1º grau.PDF"), "ana")

        path, _, length, content_type, metadata = model.upload_material.call_args.args
        self.assertEqual(path, "matematica/Funcao_1o_grau.pdf")
        self.assertEqual((length, content_type), (4, "application/pdf"))
        self.assertEqual(metadata["enviado_por"], "ana")
        self.assertFalse(model.upload_material.call_args.kwargs["overwrite"])

    @patch("services.material_service.material_model")
    def test_rejects_disallowed_and_empty_files(self, model):
        with self.assertRaises(MaterialValidationError):
            material_service.create_material("matematica", self.upload("virus.exe"), "ana")
        with self.assertRaises(MaterialValidationError):
            material_service.create_material("matematica", self.upload(conteudo=b""), "ana")
        with self.assertRaises(MaterialValidationError):
            material_service.create_material("matematica", None, "ana")
        model.upload_material.assert_not_called()

    @patch("services.material_service.material_model")
    def test_update_requires_same_extension_and_keeps_author(self, model):
        model.get_material.return_value = {"metadata": {"enviado_por": "ana"}}

        with self.assertRaises(MaterialValidationError):
            material_service.update_material("matematica", "aula.pdf", self.upload("aula.docx"), "bia")

        material_service.update_material("matematica", "aula.pdf", self.upload("nova.pdf"), "bia")
        path, _, _, _, metadata = model.upload_material.call_args.args
        self.assertEqual(path, "matematica/aula.pdf")
        self.assertEqual((metadata["enviado_por"], metadata["atualizado_por"]), ("ana", "bia"))

    @patch("services.material_service.material_model")
    def test_update_missing_returns_none(self, model):
        model.get_material.return_value = None

        self.assertIsNone(
            material_service.update_material("matematica", "aula.pdf", self.upload(), "bia")
        )
        model.upload_material.assert_not_called()


if __name__ == "__main__":
    unittest.main()
