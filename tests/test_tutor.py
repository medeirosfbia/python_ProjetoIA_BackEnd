import unittest
from unittest.mock import patch

import app as app_module
from services import chat_service, dashboard_service, tutor_context
from services.chat_service import (
    NoTutorForSubjectError,
    QuestionNotFoundError,
    QuestionNotGradedError,
    explain_question,
)

SNAPSHOT = {
    "assunto": "Matemática",
    "meta": 70.0,
    "atual": 52.5,
    "tendencia": {"direcao": "subindo", "pp_por_tentativa": 2.0},
    "topicos_fracos": [
        {"topico": "Porcentagem", "percentual": 40.0, "questoes": 5},
        {"topico": "Frações", "percentual": 50.0, "questoes": 4},
        {"topico": "Potências", "percentual": 55.0, "questoes": 3},
        {"topico": "Raízes", "percentual": 60.0, "questoes": 3},
    ],
}

EXAM = {
    "_id": "p1",
    "titulo": "Simulado",
    "contexto": {"assunto_materia": "Matemática"},
    "questoes": [
        {
            "id_questao": "q1",
            "enunciado": "Quanto é 10% de 50?",
            "opcoes": [{"id": "a", "texto": "5"}, {"id": "b", "texto": "10"}],
            "resposta_correta_id": "a",
            "explicacao_gabarito": "10% = 0,1; 0,1 x 50 = 5.",
        },
        {"id_questao": "q2", "enunciado": "Explique porcentagem.", "chave_correcao": "Parte de 100"},
    ],
}


def attempt(*itens):
    return [{"prova_id": "p1", "respostas": list(itens)}]


class TutorContextTextTestCase(unittest.TestCase):
    def test_student_context_in_portuguese(self):
        texto = tutor_context.student_context(SNAPSHOT, "pt")

        self.assertIn("Desempenho recente em Matemática: 52.5% (meta: 70%), em alta.", texto)
        # Só os 3 tópicos mais fracos
        self.assertIn("Porcentagem (40%), Frações (50%), Potências (55%)", texto)
        self.assertNotIn("Raízes", texto)

    def test_student_context_in_english_without_trend_or_topics(self):
        snapshot = {**SNAPSHOT, "tendencia": None, "topicos_fracos": []}

        texto = tutor_context.student_context(snapshot, "en")

        self.assertIn("Recent performance in Matemática: 52.5% (goal: 70%).", texto)
        self.assertNotIn("Hardest topics", texto)

    def test_no_context_without_data(self):
        self.assertIsNone(tutor_context.student_context(None, "pt"))
        self.assertIsNone(tutor_context.student_context({**SNAPSHOT, "atual": None}, "pt"))

    def test_question_context_multiple_choice(self):
        item = {"id_questao": "q1", "resposta": "b", "correta": False}

        texto = tutor_context.question_context(EXAM, EXAM["questoes"][0], item, "pt")

        self.assertIn('prova "Simulado"', texto)
        self.assertIn("Enunciado: Quanto é 10% de 50?", texto)
        self.assertIn("Resposta do aluno: 10", texto)
        self.assertIn("Resposta correta: 5", texto)
        self.assertIn("Explicação do gabarito: 10% = 0,1", texto)

    def test_question_context_blank_essay(self):
        item = {"id_questao": "q2", "resposta": None, "correta": False}

        texto = tutor_context.question_context(EXAM, EXAM["questoes"][1], item, "pt")

        self.assertIn("Resposta do aluno: (em branco)", texto)
        self.assertIn("Critério de correção: Parte de 100", texto)
        self.assertNotIn("Opções:", texto)

    def test_default_message_depends_on_result(self):
        self.assertIn("onde eu errei", tutor_context.default_question_message({"correta": False}, "pt"))
        self.assertEqual(
            tutor_context.default_question_message({"correta": True}, "en"),
            "Can you explain this question?",
        )


@patch("services.dashboard_service.exam_model")
class SubjectSnapshotTestCase(unittest.TestCase):
    def test_filters_subject_ignoring_accents_and_case(self, exam_model):
        def tentativa(assunto, acertos):
            return {"assunto_materia": assunto, "prova_id": "p", "respostas": [
                {"peso": 1, "pontos_obtidos": 1 if i < acertos else 0, "correta": i < acertos,
                 "status_correcao": "corrigida", "id_questao": f"q{i}"} for i in range(4)
            ]}
        # O model devolve as mais recentes primeiro
        exam_model.list_answers_for_dashboard.return_value = [
            tentativa("Matemática", 1), tentativa("Inglês", 4), tentativa("MATEMÁTICA", 2),
        ]

        snapshot = dashboard_service.subject_snapshot("ana", "matematica", meta=70)

        self.assertEqual(snapshot["tentativas"], 2)
        self.assertEqual(snapshot["atual"], 37.5)
        self.assertEqual(snapshot["assunto"], "Matemática")

    def test_none_without_attempts(self, exam_model):
        exam_model.list_answers_for_dashboard.return_value = []

        self.assertIsNone(dashboard_service.subject_snapshot("ana", "matematica"))


@patch("services.chat_service.ollama")
@patch("services.chat_service.update_chat")
@patch("services.chat_service.create_chat", return_value="chat-1")
@patch("services.chat_service.subject_snapshot", return_value=SNAPSHOT)
class PersonalizedChatTestCase(unittest.TestCase):
    def test_new_chat_sends_and_saves_student_profile(self, snapshot, create_chat, update_chat, ollama):
        ollama.chat.return_value = iter([])

        "".join(chat_service.query_new_chat("ana", "qwen2-math", "oi")["resposta_stream"])

        snapshot.assert_called_once_with("ana", "matematica")
        system = ollama.chat.call_args.kwargs["messages"][0]["content"]
        self.assertTrue(system.startswith(chat_service.math_context))
        self.assertIn("Porcentagem (40%)", system)
        self.assertIn("Porcentagem", create_chat.call_args.kwargs["context"]["student"])

    def test_profile_failure_does_not_break_chat(self, snapshot, create_chat, update_chat, ollama):
        snapshot.side_effect = RuntimeError("mongo fora")
        ollama.chat.return_value = iter([])

        with self.assertLogs("services.chat_service", level="ERROR"):
            "".join(chat_service.query_new_chat("ana", "llama3", "hi")["resposta_stream"])

        system = ollama.chat.call_args.kwargs["messages"][0]["content"]
        self.assertEqual(system, chat_service.english_context)

    @patch("services.chat_service.get_chat_messages")
    def test_continue_reuses_saved_context(self, get_chat_messages, snapshot, create_chat, update_chat, ollama):
        get_chat_messages.return_value = {
            "model": "qwen2-math",
            "context": {"student": "PERFIL", "question": "QUESTAO"},
            "messages": [],
        }
        ollama.chat.return_value = iter([])

        "".join(chat_service.continue_chat("ana", "chat-1", None, "e?")["resposta_stream"])

        system = ollama.chat.call_args.kwargs["messages"][0]["content"]
        self.assertEqual(system, chat_service.math_context + "\n\nPERFIL\n\nQUESTAO")
        snapshot.assert_not_called()


@patch("services.chat_service.ollama")
@patch("services.chat_service.update_chat")
@patch("services.chat_service.create_chat", return_value="chat-1")
@patch("services.chat_service.subject_snapshot", return_value=None)
@patch("services.chat_service.exam_model")
class ExplainQuestionTestCase(unittest.TestCase):
    def test_opens_chat_with_question_context(self, exam_model, snapshot, create_chat, update_chat, ollama):
        exam_model.list_answers.return_value = attempt(
            {"id_questao": "q1", "resposta": "b", "correta": False, "status_correcao": "corrigida"}
        )
        exam_model.get_exam.return_value = EXAM
        ollama.chat.return_value = iter([])

        response = explain_question("ana", "p1", "q1")
        "".join(response["resposta_stream"])

        exam_model.list_answers.assert_called_once_with({"usuario_id": "ana", "prova_id": "p1"}, limit=1)
        kwargs = ollama.chat.call_args.kwargs
        # Matemática -> tutor de matemática
        self.assertEqual(kwargs["model"], "qwen2-math")
        self.assertIn("Resposta correta: 5", kwargs["messages"][0]["content"])
        self.assertEqual(kwargs["messages"][1]["content"], "Pode me explicar onde eu errei nesta questão?")
        self.assertEqual(create_chat.call_args.kwargs["origin"], {"prova_id": "p1", "id_questao": "q1"})
        self.assertEqual(create_chat.call_args.kwargs["title"], "Revisão: Simulado")

    def test_uses_custom_message_and_model(self, exam_model, snapshot, create_chat, update_chat, ollama):
        exam_model.list_answers.return_value = attempt(
            {"id_questao": "q1", "resposta": "b", "correta": False, "status_correcao": "corrigida"}
        )
        exam_model.get_exam.return_value = {**EXAM, "contexto": {"assunto_materia": "História"}}
        ollama.chat.return_value = iter([])

        "".join(explain_question("ana", "p1", "q1", model="llama3", query="Why?")["resposta_stream"])

        kwargs = ollama.chat.call_args.kwargs
        self.assertEqual(kwargs["model"], "llama3")
        self.assertEqual(kwargs["messages"][1]["content"], "Why?")
        self.assertIn("Student's answer: 10", kwargs["messages"][0]["content"])

    def test_subject_without_tutor_requires_model(self, exam_model, snapshot, create_chat, update_chat, ollama):
        exam_model.list_answers.return_value = attempt(
            {"id_questao": "q1", "resposta": "b", "correta": False, "status_correcao": "corrigida"}
        )
        exam_model.get_exam.return_value = {**EXAM, "contexto": {"assunto_materia": "História"}}

        with self.assertRaises(NoTutorForSubjectError):
            explain_question("ana", "p1", "q1")
        create_chat.assert_not_called()

    def test_question_not_answered_or_exam_deleted(self, exam_model, snapshot, create_chat, update_chat, ollama):
        exam_model.get_exam.return_value = EXAM
        exam_model.list_answers.return_value = []
        with self.assertRaises(QuestionNotFoundError):
            explain_question("ana", "p1", "q1")

        exam_model.list_answers.return_value = attempt({"id_questao": "q1", "status_correcao": "corrigida"})
        exam_model.get_exam.return_value = None
        with self.assertRaises(QuestionNotFoundError):
            explain_question("ana", "p1", "q1")
        create_chat.assert_not_called()

    def test_pending_question_cannot_be_explained(self, exam_model, snapshot, create_chat, update_chat, ollama):
        exam_model.list_answers.return_value = attempt(
            {"id_questao": "q2", "resposta": "texto", "correta": None, "status_correcao": "pendente"}
        )
        exam_model.get_exam.return_value = EXAM

        with self.assertRaises(QuestionNotGradedError):
            explain_question("ana", "p1", "q2")


class ExplainQuestionEndpointTestCase(unittest.TestCase):
    def setUp(self):
        patchers = [
            patch.object(app_module, "authenticate_request", return_value=None),
            patch("controllers.chat_controller.authenticated_user_id", return_value="ana"),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = app_module.app.test_client()

    @patch("controllers.chat_controller.explain_question")
    def test_streams_response(self, explain):
        explain.return_value = {"chat_id": "chat-1", "resposta_stream": iter(["Vamos lá"])}

        response = self.client.post(
            "/chats/from-question", json={"prova_id": "p1", "id_questao": "q1", "message": "E aí?"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Chat-ID"], "chat-1")
        self.assertEqual(response.data, "Vamos lá".encode())
        explain.assert_called_once_with("ana", "p1", "q1", model=None, query="E aí?")

    @patch("controllers.chat_controller.explain_question")
    def test_error_codes(self, explain):
        casos = [
            (QuestionNotFoundError("x"), 404),
            (QuestionNotGradedError("x"), 409),
            (NoTutorForSubjectError("História"), 400),
        ]
        for erro, status in casos:
            explain.side_effect = erro
            response = self.client.post("/chats/from-question", json={"prova_id": "p1", "id_questao": "q1"})
            self.assertEqual(response.status_code, status)

    def test_requires_question_reference(self):
        response = self.client.post("/chats/from-question", json={"prova_id": "p1"})

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
