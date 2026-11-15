import unittest
from datetime import date, datetime
from unittest.mock import patch

import app as app_module
from models import user_activity
from services import dashboard_service as ds
from services.exam_service import ExamValidationError, grade_answers, validate_exam_payload


def item(correta, peso=1.0, topico=None, status="corrigida", id_questao="q1"):
    return {
        "id_questao": id_questao,
        "peso": peso,
        "correta": correta,
        "pontos_obtidos": None if status == "pendente" else (peso if correta else 0.0),
        "status_correcao": status,
        **({"topico": topico} if topico else {}),
    }


def answer(prova_id, acertos, total=10, assunto="Matemática", topico=None, dia=1):
    return {
        "prova_id": prova_id,
        "titulo_prova": f"Prova {prova_id}",
        "assunto_materia": assunto,
        "enviado_em": datetime(2026, 10, dia, 12, 0),
        "respostas": [
            item(i < acertos, topico=topico, id_questao=f"q{i}") for i in range(total)
        ],
    }


def exam(prova_id, assunto="Matemática", permite_refazer=True):
    return {
        "_id": prova_id,
        "titulo": f"Prova {prova_id}",
        "contexto": {"assunto_materia": assunto},
        "configuracoes_teste": {"permite_refazer": permite_refazer},
    }


class CalculationsTestCase(unittest.TestCase):
    def test_percentual_ignores_pending_and_counts_blank_as_zero(self):
        tentativa = {"respostas": [
            item(True, peso=2.0),
            item(None, peso=5.0, status="pendente"),
            item(False, peso=2.0, status="em_branco"),
        ]}

        self.assertEqual(ds.attempt_percentual(tentativa), 50.0)

    def test_percentual_is_none_when_everything_is_pending(self):
        tentativa = {"respostas": [item(None, status="pendente")]}

        self.assertIsNone(ds.attempt_percentual(tentativa))

    def test_trend_needs_three_attempts(self):
        self.assertIsNone(ds.trend([50, 60]))

    def test_trend_direction(self):
        self.assertEqual(ds.trend([40, 50, 60]), {"direcao": "subindo", "pp_por_tentativa": 10.0})
        self.assertEqual(ds.trend([60, 50, 40])["direcao"], "caindo")
        self.assertEqual(ds.trend([50, 50.5, 50])["direcao"], "estavel")

    def test_trend_uses_only_last_ten_attempts(self):
        # Começo ruim e depois estável: só a parte recente importa
        valores = [0, 10, 20] + [70] * 10

        self.assertEqual(ds.trend(valores)["pp_por_tentativa"], 0.0)

    def test_projection(self):
        subindo = {"direcao": "subindo", "pp_por_tentativa": 2.0}
        self.assertEqual(ds.projection(75, subindo, 70), 0)
        self.assertEqual(ds.projection(63, subindo, 70), 4)
        self.assertIsNone(ds.projection(63, {"direcao": "caindo", "pp_por_tentativa": -2.0}, 70))
        self.assertIsNone(ds.projection(10, {"direcao": "subindo", "pp_por_tentativa": 1.1}, 70))
        self.assertIsNone(ds.projection(63, None, 70))

    def test_summarize(self):
        valores = [40, 50, 60, 50, 50, 50, 50, 50, 70, 70, 70, 70]

        resumo = ds.summarize(valores, 70)

        self.assertEqual(resumo["tentativas"], 12)
        self.assertEqual(resumo["inicio"], 50.0)        # 40, 50, 60
        self.assertEqual(resumo["anterior"], 52.0)      # 60, 50, 50, 50, 50
        self.assertEqual(resumo["atual"], 66.0)         # 50, 70, 70, 70, 70
        self.assertEqual(resumo["variacao"], 14.0)
        self.assertEqual(resumo["gap"], 4.0)

    def test_summarize_without_attempts(self):
        resumo = ds.summarize([], 70)

        self.assertEqual(resumo["tentativas"], 0)
        self.assertIsNone(resumo["atual"])
        self.assertIsNone(resumo["gap"])
        self.assertIsNone(resumo["anterior"])

    def test_weak_topics(self):
        tentativas = [
            {"respostas": [
                item(False, topico="Porcentagem"), item(False, topico="porcentagem "),
                item(True, topico="Porcentagem"),
                item(True, topico="Equações"), item(True, topico="Equações"), item(True, topico="Equações"),
                item(False, topico="Frações"), item(False, topico="Frações"),
            ]}
        ]

        fracos = ds.weak_topics(tentativas, 70)

        # Equações está acima da meta; Frações tem só 2 questões
        self.assertEqual(fracos, [{"topico": "Porcentagem", "percentual": 33.3, "questoes": 3}])

    def test_wrong_questions_use_latest_attempt_of_each_exam(self):
        primeira = answer("p1", acertos=0, total=2)
        refeita = answer("p1", acertos=2, total=2)
        outra = answer("p2", acertos=1, total=2)

        erradas = ds.wrong_questions([primeira, refeita, outra])

        self.assertEqual([(e["prova_id"], e["id_questao"]) for e in erradas], [("p2", "q1")])

    def test_subject_actions(self):
        respostas = [answer("p1", acertos=4), answer("p2", acertos=3), answer("p3", acertos=9)]
        publicadas = [
            exam("p1"), exam("p2", permite_refazer=False), exam("p3"),
            exam("p4"), exam("p5", assunto="Inglês"),
        ]

        acoes = ds.subject_actions("Matemática", respostas, publicadas, 70)

        self.assertEqual(acoes["provas_nao_feitas"], [{"prova_id": "p4", "titulo": "Prova p4"}])
        self.assertEqual(acoes["refazer"], [{"prova_id": "p1", "titulo": "Prova p1", "percentual": 40.0}])
        self.assertEqual(acoes["pasta_materiais"], "matematica")

    def test_consistency(self):
        dias = ["2026-11-03", "2026-11-02", "2026-11-01", "2026-10-30", "2026-10-10"]

        constancia = ds.consistency(dias, date(2026, 11, 4))

        # Hoje ainda sem uso: a sequência conta a partir de ontem
        self.assertEqual(constancia, {"dias_seguidos": 3, "dias_ultimos_7": 4, "dias_ultimos_30": 5})


@patch("services.dashboard_service.local_today", return_value="2026-11-04")
@patch("services.dashboard_service.user_activity_model")
@patch("services.dashboard_service.exam_model")
class BuildDashboardTestCase(unittest.TestCase):
    def test_builds_full_dashboard(self, exam_model, activity_model, local_today):
        pendente = {**answer("p9", 0, dia=20), "respostas": [item(None, status="pendente")]}
        tentativas = [
            answer("p1", 3, dia=1), answer("p1", 5, dia=2), answer("p1", 6, dia=3),
            answer("i1", 9, assunto="Inglês", dia=4), pendente,
        ]
        # O model devolve as mais recentes primeiro
        exam_model.list_answers_for_dashboard.return_value = list(reversed(tentativas))
        exam_model.list_exams.return_value = [exam("p1"), exam("p2"), exam("i1", "Inglês"), exam("h1", "História")]
        activity_model.list_active_days.return_value = ["2026-11-04", "2026-11-03"]

        dashboard = ds.build_dashboard("ana", meta=70)

        exam_model.list_answers_for_dashboard.assert_called_once_with("ana")
        activity_model.list_active_days.assert_called_once_with("ana", "2026-08-07")
        self.assertEqual(dashboard["meta_percentual"], 70)
        self.assertEqual(dashboard["aguardando_correcao"], 1)
        self.assertEqual(dashboard["geral"]["tentativas"], 4)
        self.assertEqual(
            [e["percentual"] for e in dashboard["geral"]["evolucao"]], [30.0, 50.0, 60.0, 90.0]
        )
        self.assertEqual(dashboard["geral"]["evolucao"][0]["data"], "2026-10-01T12:00:00+00:00")

        matematica, ingles = dashboard["por_materia"]
        self.assertEqual(matematica["assunto"], "Matemática")
        self.assertEqual(matematica["tendencia"]["direcao"], "subindo")
        self.assertEqual(matematica["acoes"]["provas_nao_feitas"], [{"prova_id": "p2", "titulo": "Prova p2"}])
        self.assertEqual(ingles["gap"], 0.0)
        self.assertIsNone(ingles["acoes"])

        self.assertEqual(dashboard["dados_insuficientes"], ["Inglês"])
        self.assertEqual(dashboard["materias_nao_iniciadas"], ["História"])
        self.assertEqual(dashboard["constancia"]["dias_seguidos"], 2)

    def test_new_user_gets_empty_dashboard(self, exam_model, activity_model, local_today):
        exam_model.list_answers_for_dashboard.return_value = []
        exam_model.list_exams.return_value = [exam("p1")]
        activity_model.list_active_days.return_value = ["2026-11-04"]

        dashboard = ds.build_dashboard("ana", meta=70)

        self.assertEqual(dashboard["geral"]["tentativas"], 0)
        self.assertEqual(dashboard["geral"]["evolucao"], [])
        self.assertEqual(dashboard["por_materia"], [])
        self.assertEqual(dashboard["materias_nao_iniciadas"], ["Matemática"])


class DashboardEndpointTestCase(unittest.TestCase):
    @patch("controllers.dashboard_controller.build_dashboard", return_value={"meta_percentual": 70})
    @patch("controllers.dashboard_controller.authenticated_user_id", return_value="ana")
    @patch.object(app_module, "authenticate_request", return_value=None)
    def test_returns_dashboard_of_authenticated_user(self, auth, user_id, build):
        response = app_module.app.test_client().get("/dashboard/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"meta_percentual": 70})
        build.assert_called_once_with("ana")


class ExamTopicTestCase(unittest.TestCase):
    def payload(self, topico):
        return {
            "titulo": "Simulado",
            "contexto": {"assunto_materia": "Matemática"},
            "questoes": [{
                "id_questao": "q1",
                "tipo": "multipla_escolha",
                "peso": 1,
                "enunciado": "2 + 2?",
                "opcoes": [{"id": "a", "texto": "4"}, {"id": "b", "texto": "5"}],
                "resposta_correta_id": "a",
                **({"topico": topico} if topico is not None else {}),
            }],
        }

    def test_topic_is_optional_and_stripped(self):
        sem = validate_exam_payload(self.payload(None))["questoes"][0]
        com = validate_exam_payload(self.payload("  Soma "))["questoes"][0]

        self.assertNotIn("topico", sem)
        self.assertEqual(com["topico"], "Soma")

    def test_rejects_invalid_topic(self):
        for invalido in (123, "x" * 81):
            with self.assertRaises(ExamValidationError):
                validate_exam_payload(self.payload(invalido))

    def test_topic_is_copied_to_graded_answer(self):
        prova = validate_exam_payload(self.payload("Soma"))

        correcao = grade_answers(prova, {"respostas": [{"id_questao": "q1", "resposta": "b"}]})

        self.assertEqual(correcao["respostas"][0]["topico"], "Soma")


class ActivityDaysTestCase(unittest.TestCase):
    @patch("models.user_activity.user_activity_days_collection")
    @patch("models.user_activity.user_activity_collection")
    def test_mark_active_keeps_last_day_and_history(self, last_day, days):
        user_activity.mark_active("ana", "2026-11-04")

        self.assertEqual(last_day.update_one.call_args.args[0], {"user_id": "ana"})
        days.update_one.assert_called_once()
        filtro, update = days.update_one.call_args.args
        self.assertEqual(filtro, {"user_id": "ana", "day": "2026-11-04"})
        self.assertIn("$setOnInsert", update)
        self.assertTrue(days.update_one.call_args.kwargs["upsert"])


if __name__ == "__main__":
    unittest.main()
