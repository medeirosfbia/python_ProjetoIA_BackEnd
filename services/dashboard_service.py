import math
import os
from datetime import date, datetime, timedelta, timezone

from models import exam as exam_model
from models import user_activity as user_activity_model
from services.activity_service import local_today
from services.exam_service import STATUS_PUBLICADO
from services.material_service import MaterialValidationError, normalize_conteudo

META_PERCENTUAL = float(os.getenv("DASHBOARD_META_PERCENTUAL", "70"))

TENTATIVAS_INICIO = 3          # "onde estava": média das primeiras tentativas
TENTATIVAS_ATUAL = 5           # "onde está": média das últimas tentativas
TENTATIVAS_TENDENCIA = 10      # janela da regressão linear
MIN_TENTATIVAS_TENDENCIA = 3   # abaixo disso a tendência não é confiável
LIMIAR_TENDENCIA = 1.0         # p.p. por tentativa para considerar subindo/caindo
MAX_PROJECAO = 50              # acima disso a projeção não tem utilidade
MIN_QUESTOES_TOPICO = 3
QUESTOES_TOPICO_RECENTES = 20
MAX_ITENS_ACAO = 5
MAX_EVOLUCAO = 50
DIAS_CONSTANCIA = 90


# ---------------------------------------------------------------------------
# Cálculos (funções puras)
# ---------------------------------------------------------------------------

def _graded_items(answer):
    # Dissertativas pendentes ficam de fora até serem corrigidas
    return [
        item for item in answer.get("respostas", [])
        if item.get("status_correcao") != "pendente"
    ]


def _percentual(items):
    possiveis = sum(item.get("peso") or 0 for item in items)
    if not possiveis:
        return None
    obtidos = sum(item.get("pontos_obtidos") or 0 for item in items)
    return round(100 * obtidos / possiveis, 1)


def attempt_percentual(answer):
    """Desempenho da tentativa (0-100) considerando só as questões já corrigidas."""
    return _percentual(_graded_items(answer))


def _mean(values):
    return round(sum(values) / len(values), 1) if values else None


def trend(values):
    """Inclinação da regressão linear das últimas tentativas, em p.p. por tentativa."""
    recentes = values[-TENTATIVAS_TENDENCIA:]
    n = len(recentes)
    if n < MIN_TENTATIVAS_TENDENCIA:
        return None

    media_x = (n - 1) / 2
    media_y = sum(recentes) / n
    numerador = sum((x - media_x) * (y - media_y) for x, y in enumerate(recentes))
    denominador = sum((x - media_x) ** 2 for x in range(n))
    inclinacao = round(numerador / denominador, 2)

    if inclinacao > LIMIAR_TENDENCIA:
        direcao = "subindo"
    elif inclinacao < -LIMIAR_TENDENCIA:
        direcao = "caindo"
    else:
        direcao = "estavel"
    return {"direcao": direcao, "pp_por_tentativa": inclinacao}


def projection(atual, tendencia, meta):
    """Tentativas estimadas até a meta no ritmo atual (0 se já atingiu, None se não há como estimar)."""
    if atual is None:
        return None
    if atual >= meta:
        return 0
    if not tendencia or tendencia["pp_por_tentativa"] <= 0:
        return None
    tentativas = math.ceil((meta - atual) / tendencia["pp_por_tentativa"])
    return tentativas if tentativas <= MAX_PROJECAO else None


def summarize(values, meta):
    """Onde estava, onde está, tendência e distância até a meta de uma série de percentuais."""
    inicio = _mean(values[:TENTATIVAS_INICIO])
    anterior = _mean(values[-2 * TENTATIVAS_ATUAL:-TENTATIVAS_ATUAL])
    atual = _mean(values[-TENTATIVAS_ATUAL:])
    tendencia = trend(values)
    return {
        "tentativas": len(values),
        "inicio": inicio,
        "anterior": anterior,
        "atual": atual,
        "variacao": round(atual - anterior, 1) if atual is not None and anterior is not None else None,
        "tendencia": tendencia,
        "gap": round(max(0.0, meta - atual), 1) if atual is not None else None,
        "projecao_tentativas_ate_meta": projection(atual, tendencia, meta),
    }


def weak_topics(answers, meta):
    """Tópicos abaixo da meta nas questões recentes, do pior para o melhor."""
    por_topico = {}
    for answer in answers:
        for item in _graded_items(answer):
            topico = (item.get("topico") or "").strip()
            if topico:
                # Agrupa ignorando maiúsculas; mantém o nome mais recente para exibir
                grupo = por_topico.setdefault(topico.casefold(), {"nome": topico, "itens": []})
                grupo["nome"] = topico
                grupo["itens"].append(item)

    fracos = []
    for grupo in por_topico.values():
        itens = grupo["itens"][-QUESTOES_TOPICO_RECENTES:]
        percentual = _percentual(itens)
        if len(itens) >= MIN_QUESTOES_TOPICO and percentual is not None and percentual < meta:
            fracos.append({"topico": grupo["nome"], "percentual": percentual, "questoes": len(itens)})
    return sorted(fracos, key=lambda t: t["percentual"])


def _latest_by_exam(answers):
    ultimas = {}
    for answer in answers:
        ultimas[answer["prova_id"]] = answer
    return ultimas


def wrong_questions(answers):
    """Questões erradas ou em branco na última tentativa de cada prova (mais recentes primeiro)."""
    erradas = []
    for answer in reversed(list(_latest_by_exam(answers).values())):
        for item in answer.get("respostas", []):
            if item.get("correta") is False:
                erradas.append({
                    "prova_id": answer["prova_id"],
                    "titulo_prova": answer.get("titulo_prova"),
                    "id_questao": item["id_questao"],
                    "topico": item.get("topico"),
                    "explicacao_gabarito": item.get("explicacao_gabarito"),
                })
    return erradas[:MAX_ITENS_ACAO]


def subject_actions(assunto, answers, published_exams, meta):
    """O que fazer para chegar à meta numa matéria."""
    da_materia = [
        exam for exam in published_exams
        if exam.get("contexto", {}).get("assunto_materia") == assunto
    ]
    respondidas = {answer["prova_id"] for answer in answers}
    ultimas = _latest_by_exam(answers)

    refazer = []
    for exam in da_materia:
        ultima = ultimas.get(exam["_id"])
        if not ultima or not exam.get("configuracoes_teste", {}).get("permite_refazer", True):
            continue
        percentual = attempt_percentual(ultima)
        if percentual is not None and percentual < meta:
            refazer.append({"prova_id": exam["_id"], "titulo": exam.get("titulo"), "percentual": percentual})

    pasta = subject_key(assunto)

    return {
        "provas_nao_feitas": [
            {"prova_id": exam["_id"], "titulo": exam.get("titulo")}
            for exam in da_materia if exam["_id"] not in respondidas
        ][:MAX_ITENS_ACAO],
        "refazer": sorted(refazer, key=lambda p: p["percentual"])[:MAX_ITENS_ACAO],
        "questoes_erradas": wrong_questions(answers),
        "pasta_materiais": pasta,
    }


def consistency(active_days, today):
    """Sequência de dias seguidos (até hoje ou ontem) e dias de uso recentes."""
    dias = {date.fromisoformat(day) for day in active_days}

    sequencia = 0
    cursor = today if today in dias else today - timedelta(days=1)
    while cursor in dias:
        sequencia += 1
        cursor -= timedelta(days=1)

    return {
        "dias_seguidos": sequencia,
        "dias_ultimos_7": sum(1 for d in dias if today - d < timedelta(days=7)),
        "dias_ultimos_30": sum(1 for d in dias if today - d < timedelta(days=30)),
    }


def subject_key(assunto):
    """Chave para comparar matérias ignorando acentos e maiúsculas ("Matemática" -> "matematica")."""
    try:
        return normalize_conteudo(assunto)
    except MaterialValidationError:
        return None


def _iso(value):
    if isinstance(value, datetime):
        # O PyMongo devolve datas UTC sem fuso
        return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()
    return value


# ---------------------------------------------------------------------------
# Montagem do dashboard
# ---------------------------------------------------------------------------

def build_dashboard(user_id: str, meta: float = META_PERCENTUAL) -> dict:
    answers = list(reversed(exam_model.list_answers_for_dashboard(user_id)))
    published_exams = exam_model.list_exams({"status": STATUS_PUBLICADO}, limit=500)

    avaliadas = []
    aguardando_correcao = 0
    for answer in answers:
        percentual = attempt_percentual(answer)
        if percentual is None:
            aguardando_correcao += 1
        else:
            avaliadas.append((answer, percentual))

    geral = summarize([p for _, p in avaliadas], meta)
    geral["evolucao"] = [
        {
            "data": _iso(answer.get("enviado_em")),
            "percentual": percentual,
            "assunto": answer.get("assunto_materia"),
            "prova_id": answer.get("prova_id"),
            "titulo_prova": answer.get("titulo_prova"),
        }
        for answer, percentual in avaliadas[-MAX_EVOLUCAO:]
    ]

    materias = {}
    for answer, percentual in avaliadas:
        materias.setdefault(answer.get("assunto_materia") or "Sem matéria", []).append((answer, percentual))

    por_materia = []
    for assunto, itens in materias.items():
        respostas = [answer for answer, _ in itens]
        resumo = summarize([p for _, p in itens], meta)
        por_materia.append({
            "assunto": assunto,
            **resumo,
            "topicos_fracos": weak_topics(respostas, meta),
            # Ações só onde ainda falta chegar à meta
            "acoes": subject_actions(assunto, respostas, published_exams, meta) if resumo["gap"] else None,
        })
    por_materia.sort(key=lambda m: (-(m["gap"] or 0), m["assunto"]))

    respondidas = {answer["prova_id"] for answer in answers}
    today = date.fromisoformat(local_today())
    desde = (today - timedelta(days=DIAS_CONSTANCIA - 1)).isoformat()

    return {
        "meta_percentual": meta,
        "geral": geral,
        "por_materia": por_materia,
        "dados_insuficientes": [
            m["assunto"] for m in por_materia if m["tentativas"] < MIN_TENTATIVAS_TENDENCIA
        ],
        "materias_nao_iniciadas": sorted({
            exam.get("contexto", {}).get("assunto_materia")
            for exam in published_exams
            if exam.get("contexto", {}).get("assunto_materia")
            and exam["_id"] not in respondidas
        } - set(materias)),
        "aguardando_correcao": aguardando_correcao,
        "constancia": consistency(user_activity_model.list_active_days(user_id, desde), today),
    }


def subject_snapshot(user_id: str, materia: str, meta: float = META_PERCENTUAL):
    """Desempenho do usuário numa matéria (chave de subject_key), ou None sem tentativas avaliadas."""
    answers = [
        answer for answer in reversed(exam_model.list_answers_for_dashboard(user_id))
        if subject_key(answer.get("assunto_materia")) == materia
    ]
    valores = [p for p in map(attempt_percentual, answers) if p is not None]
    if not valores:
        return None
    return {
        "assunto": answers[-1].get("assunto_materia"),
        "meta": meta,
        **summarize(valores, meta),
        "topicos_fracos": weak_topics(answers, meta),
    }
