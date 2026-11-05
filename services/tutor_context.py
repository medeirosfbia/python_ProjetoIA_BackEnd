"""Textos extras do prompt do tutor: perfil do aluno e questão em revisão.

Os textos seguem o idioma do tutor (o de Inglês tem prompt em inglês).
"""

MAX_TOPICOS = 3
MAX_RESPOSTA_ALUNO = 2000

TEXTOS = {
    "pt": {
        "perfil": (
            "Perfil do aluno (use para ajustar o nível e escolher exemplos; não cite estes "
            "números, a menos que o aluno pergunte sobre o próprio desempenho):"
        ),
        "desempenho": "- Desempenho recente em {assunto}: {atual}% (meta: {meta}%){tendencia}.",
        "tendencia": {"subindo": ", em alta", "estavel": ", estável", "caindo": ", em queda"},
        "topicos": "- Tópicos com mais dificuldade: {topicos}. Dê atenção especial a eles quando surgirem.",
        "questao": (
            "Esta conversa foi aberta a partir de uma questão já corrigida da prova \"{titulo}\". "
            "Ajude o aluno a entender o raciocínio e onde ele errou, passo a passo. Como a questão "
            "já foi corrigida, nesta conversa você pode mostrar a resposta correta."
        ),
        "enunciado": "Enunciado: {texto}",
        "opcoes": "Opções:",
        "resposta_aluno": "Resposta do aluno: {texto}",
        "em_branco": "(em branco)",
        "resposta_correta": "Resposta correta: {texto}",
        "explicacao": "Explicação do gabarito: {texto}",
        "criterio": "Critério de correção: {texto}",
        "pergunta_erro": "Pode me explicar onde eu errei nesta questão?",
        "pergunta_acerto": "Pode me explicar esta questão?",
    },
    "en": {
        "perfil": (
            "Student profile (use it to adjust the level and pick examples; do not mention these "
            "numbers unless the student asks about their own performance):"
        ),
        "desempenho": "- Recent performance in {assunto}: {atual}% (goal: {meta}%){tendencia}.",
        "tendencia": {"subindo": ", improving", "estavel": ", stable", "caindo": ", declining"},
        "topicos": "- Hardest topics: {topicos}. Give them extra attention when they come up.",
        "questao": (
            "This conversation was opened from an already graded question of the exam \"{titulo}\". "
            "Help the student understand the reasoning and where they went wrong, step by step. "
            "Since the question was already graded, you may show the correct answer in this conversation."
        ),
        "enunciado": "Question: {texto}",
        "opcoes": "Options:",
        "resposta_aluno": "Student's answer: {texto}",
        "em_branco": "(blank)",
        "resposta_correta": "Correct answer: {texto}",
        "explicacao": "Answer key explanation: {texto}",
        "criterio": "Grading criteria: {texto}",
        "pergunta_erro": "Can you explain where I went wrong in this question?",
        "pergunta_acerto": "Can you explain this question?",
    },
}


def _fmt(numero):
    return f"{numero:g}"


def student_context(snapshot, idioma):
    """Perfil do aluno numa matéria (saída de dashboard_service.subject_snapshot)."""
    if not snapshot or snapshot.get("atual") is None:
        return None

    textos = TEXTOS[idioma]
    tendencia = snapshot.get("tendencia") or {}
    linhas = [
        textos["perfil"],
        textos["desempenho"].format(
            assunto=snapshot["assunto"],
            atual=_fmt(snapshot["atual"]),
            meta=_fmt(snapshot["meta"]),
            tendencia=textos["tendencia"].get(tendencia.get("direcao"), ""),
        ),
    ]
    topicos = snapshot.get("topicos_fracos", [])[:MAX_TOPICOS]
    if topicos:
        linhas.append(textos["topicos"].format(topicos=", ".join(
            f"{t['topico']} ({_fmt(t['percentual'])}%)" for t in topicos
        )))
    return "\n".join(linhas)


def question_context(exam, questao, item, idioma):
    """Contexto da questão em revisão: enunciado, resposta do aluno e gabarito."""
    textos = TEXTOS[idioma]
    opcoes = {opcao["id"]: opcao["texto"] for opcao in questao.get("opcoes", [])}

    resposta = item.get("resposta")
    if resposta is None:
        resposta = textos["em_branco"]
    else:
        resposta = opcoes.get(resposta, resposta)[:MAX_RESPOSTA_ALUNO]

    linhas = [
        textos["questao"].format(titulo=exam.get("titulo", "")),
        textos["enunciado"].format(texto=questao["enunciado"]),
    ]
    if opcoes:
        linhas.append(textos["opcoes"])
        linhas.extend(f"- {texto}" for texto in opcoes.values())
    linhas.append(textos["resposta_aluno"].format(texto=resposta))

    correta = questao.get("resposta_correta_id")
    if correta in opcoes:
        linhas.append(textos["resposta_correta"].format(texto=opcoes[correta]))
    if questao.get("explicacao_gabarito"):
        linhas.append(textos["explicacao"].format(texto=questao["explicacao_gabarito"]))
    if questao.get("chave_correcao"):
        linhas.append(textos["criterio"].format(texto=questao["chave_correcao"]))
    return "\n".join(linhas)


def default_question_message(item, idioma):
    chave = "pergunta_acerto" if item.get("correta") is True else "pergunta_erro"
    return TEXTOS[idioma][chave]
