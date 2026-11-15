import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from pymongo.errors import DuplicateKeyError

from services import exam_service

EXAMPLE = json.loads(
    (Path(__file__).resolve().parents[1] / "seeds" / "exam_example.json").read_text(
        encoding="utf-8"
    )
)


def example_exam(**config):
    campos = exam_service.validate_exam_payload(copy.deepcopy(EXAMPLE))
    campos["configuracoes_teste"].update(config)
    return {"_id": "prova-1", **campos}


ALL_CORRECT = [
    {"id_questao": "q1", "resposta": "op_b"},
    {"id_questao": "q2", "resposta": "op_c"},
    {"id_questao": "q3", "resposta": "op_c"},
    {"id_questao": "q4", "resposta": "op_b"},
    {"id_questao": "q5", "resposta": "Δ = 36, x = 5 ou x = -1"},
]


class ExamValidationTestCase(unittest.TestCase):
    def test_example_exam_is_valid(self):
        campos = exam_service.validate_exam_payload(copy.deepcopy(EXAMPLE))

        self.assertEqual(campos["total_questoes"], 5)
        self.assertEqual(campos["status"], "APROVADO")
        self.assertEqual([q["ordem"] for q in campos["questoes"]], [1, 2, 3, 4, 5])

    def test_rejects_missing_required_fields(self):
        with self.assertRaises(exam_service.ExamValidationError) as ctx:
            exam_service.validate_exam_payload({"questoes": []})

        self.assertIn("titulo é obrigatório", ctx.exception.errors)
        self.assertIn("contexto.assunto_materia é obrigatório", ctx.exception.errors)
        self.assertIn(
            "questoes deve ser uma lista com pelo menos uma questão",
            ctx.exception.errors,
        )

    def test_rejects_correct_answer_that_is_not_an_option(self):
        payload = copy.deepcopy(EXAMPLE)
        payload["questoes"][0]["resposta_correta_id"] = "op_z"

        with self.assertRaises(exam_service.ExamValidationError) as ctx:
            exam_service.validate_exam_payload(payload)

        self.assertEqual(
            ctx.exception.errors,
            ["questoes[0].resposta_correta_id deve ser o id de uma das opções"],
        )

    def test_rejects_duplicated_question_ids(self):
        payload = copy.deepcopy(EXAMPLE)
        payload["questoes"][1]["id_questao"] = "q1"

        with self.assertRaises(exam_service.ExamValidationError) as ctx:
            exam_service.validate_exam_payload(payload)

        self.assertEqual(ctx.exception.errors, ["questoes[1].id_questao 'q1' está duplicado"])

    def test_drops_unknown_fields(self):
        payload = copy.deepcopy(EXAMPLE)
        payload["campo_estranho"] = "x"
        payload["questoes"][0]["campo_estranho"] = "x"

        campos = exam_service.validate_exam_payload(payload)

        self.assertNotIn("campo_estranho", campos)
        self.assertNotIn("campo_estranho", campos["questoes"][0])

    def test_hide_answer_key_removes_gabarito(self):
        exam = exam_service.hide_answer_key(example_exam())

        for questao in exam["questoes"]:
            for campo in exam_service.CAMPOS_GABARITO:
                self.assertNotIn(campo, questao)
        self.assertEqual(len(exam["questoes"][0]["opcoes"]), 4)


class ExamGradingTestCase(unittest.TestCase):
    def test_grades_multiple_choice_and_leaves_essay_pending(self):
        correcao = exam_service.grade_answers(example_exam(), {"respostas": ALL_CORRECT})

        resultado = correcao["resultado"]
        self.assertEqual(resultado["acertos"], 4)
        self.assertEqual(resultado["pontos_obtidos"], 8.0)
        self.assertEqual(resultado["pontos_possiveis"], 10.0)
        self.assertEqual(resultado["nota_obtida"], 8.0)
        self.assertEqual(resultado["questoes_pendentes_correcao"], 1)
        self.assertFalse(resultado["correcao_concluida"])
        self.assertEqual(correcao["respostas"][4]["status_correcao"], "pendente")

    def test_wrong_and_blank_answers_score_zero(self):
        respostas = [
            {"id_questao": "q1", "resposta": "op_a"},
            {"id_questao": "q5", "resposta": "   "},
        ]

        correcao = exam_service.grade_answers(example_exam(), {"respostas": respostas})

        por_questao = {item["id_questao"]: item for item in correcao["respostas"]}
        self.assertFalse(por_questao["q1"]["correta"])
        self.assertEqual(por_questao["q1"]["resposta_correta_id"], "op_b")
        self.assertEqual(por_questao["q2"]["status_correcao"], "em_branco")
        self.assertEqual(por_questao["q5"]["status_correcao"], "em_branco")
        self.assertEqual(correcao["resultado"]["nota_obtida"], 0.0)
        self.assertTrue(correcao["resultado"]["correcao_concluida"])

    def test_rejects_invalid_answers(self):
        respostas = [
            {"id_questao": "q1", "resposta": "op_z"},
            {"id_questao": "q9", "resposta": "op_a"},
            {"id_questao": "q5", "resposta": "x" * 1001},
        ]

        with self.assertRaises(exam_service.ExamValidationError) as ctx:
            exam_service.grade_answers(example_exam(), {"respostas": respostas})

        self.assertEqual(len(ctx.exception.errors), 3)


@patch("services.exam_service.exam_model")
class SubmitAnswersTestCase(unittest.TestCase):
    def test_stores_attempt_with_next_number(self, exam_model):
        exam_model.get_exam.return_value = example_exam()
        exam_model.count_attempts.return_value = 2

        answer = exam_service.submit_answers(
            "prova-1", "user-1", False, {"respostas": ALL_CORRECT, "tempo_gasto_segundos": 600}
        )

        self.assertEqual(answer["tentativa"], 3)
        self.assertEqual(answer["usuario_id"], "user-1")
        self.assertEqual(answer["assunto_materia"], "Matemática")
        self.assertEqual(answer["tempo_gasto_segundos"], 600)
        exam_model.insert_answer.assert_called_once_with(answer)

    def test_blocks_retake_when_not_allowed(self, exam_model):
        exam_model.get_exam.return_value = example_exam(permite_refazer=False)
        exam_model.count_attempts.return_value = 1

        with self.assertRaises(exam_service.ExamConflictError):
            exam_service.submit_answers("prova-1", "user-1", False, {"respostas": ALL_CORRECT})

        exam_model.insert_answer.assert_not_called()

    def test_concurrent_duplicate_attempt_is_a_conflict(self, exam_model):
        exam_model.get_exam.return_value = example_exam()
        exam_model.count_attempts.return_value = 0
        exam_model.insert_answer.side_effect = DuplicateKeyError("dup")

        with self.assertRaises(exam_service.ExamConflictError):
            exam_service.submit_answers("prova-1", "user-1", False, {"respostas": ALL_CORRECT})

    def test_students_cannot_answer_draft_exams(self, exam_model):
        exam = example_exam()
        exam["status"] = "RASCUNHO"
        exam_model.get_exam.return_value = exam

        answer = exam_service.submit_answers("prova-1", "user-1", False, {"respostas": ALL_CORRECT})

        self.assertIsNone(answer)
        exam_model.insert_answer.assert_not_called()

    def test_update_keeps_original_creator(self, exam_model):
        exam_model.get_exam.return_value = {
            "_id": "prova-1",
            "contexto": {"criado_por": {"usuario_id": "admin-1"}, "data_criacao": "ontem"},
        }
        exam_model.replace_exam.return_value = True

        exam = exam_service.update_exam("prova-1", "admin-2", copy.deepcopy(EXAMPLE))

        self.assertEqual(exam["contexto"]["criado_por"], {"usuario_id": "admin-1"})
        self.assertEqual(exam["contexto"]["data_criacao"], "ontem")
        self.assertEqual(exam["contexto"]["atualizado_por"], {"usuario_id": "admin-2"})


if __name__ == "__main__":
    unittest.main()
