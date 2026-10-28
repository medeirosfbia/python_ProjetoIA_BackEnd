from datetime import datetime, timezone
from uuid import uuid4

from pymongo.errors import DuplicateKeyError

from models import exam as exam_model

STATUS_PUBLICADO = "APROVADO"
STATUS_VALIDOS = ("RASCUNHO", "APROVADO", "ARQUIVADO")
TIPOS_QUESTAO = ("multipla_escolha", "dissertativa", "desafio_codigo")

# Campos que só admins podem ver antes de o usuário responder a prova
CAMPOS_GABARITO = (
    "resposta_correta_id",
    "explicacao_gabarito",
    "chave_correcao",
    "casos_de_teste",
)


class ExamValidationError(ValueError):
    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


class ExamConflictError(Exception):
    pass


def _now():
    return datetime.now(timezone.utc)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_positive_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _non_empty_str(value):
    return isinstance(value, str) and bool(value.strip())


def _optional_str(source, field, prefix, errors):
    value = source.get(field)
    if value is None:
        return {}
    if not isinstance(value, str):
        errors.append(f"{prefix}.{field} deve ser texto")
        return {}
    return {field: value}


# ---------------------------------------------------------------------------
# Validação das provas
# ---------------------------------------------------------------------------

def _validate_multipla_escolha(questao, prefix, errors):
    opcoes = questao.get("opcoes")
    if not isinstance(opcoes, list) or len(opcoes) < 2:
        errors.append(f"{prefix}.opcoes deve ter pelo menos duas opções")
        return {}

    ids_opcoes = []
    opcoes_validas = []
    for i, opcao in enumerate(opcoes):
        if (
            not isinstance(opcao, dict)
            or not _non_empty_str(opcao.get("id"))
            or not _non_empty_str(opcao.get("texto"))
        ):
            errors.append(f"{prefix}.opcoes[{i}] precisa de id e texto")
            continue
        if opcao["id"] in ids_opcoes:
            errors.append(f"{prefix}.opcoes[{i}].id '{opcao['id']}' está duplicado")
            continue
        ids_opcoes.append(opcao["id"])
        opcoes_validas.append({"id": opcao["id"], "texto": opcao["texto"]})

    resposta_correta = questao.get("resposta_correta_id")
    if resposta_correta not in ids_opcoes:
        errors.append(f"{prefix}.resposta_correta_id deve ser o id de uma das opções")

    return {
        "opcoes": opcoes_validas,
        "resposta_correta_id": resposta_correta,
        **_optional_str(questao, "explicacao_gabarito", prefix, errors),
    }


def _validate_dissertativa(questao, prefix, errors):
    campos = _optional_str(questao, "chave_correcao", prefix, errors)
    limite = questao.get("limite_caracteres")
    if limite is not None:
        if _is_int(limite) and limite > 0:
            campos["limite_caracteres"] = limite
        else:
            errors.append(f"{prefix}.limite_caracteres deve ser um inteiro positivo")
    return campos


def _validate_desafio_codigo(questao, prefix, errors):
    campos = {
        **_optional_str(questao, "linguagem_permitida", prefix, errors),
        **_optional_str(questao, "codigo_inicial", prefix, errors),
    }
    casos = questao.get("casos_de_teste")
    if casos is None:
        return campos
    if not isinstance(casos, list):
        errors.append(f"{prefix}.casos_de_teste deve ser uma lista")
        return campos

    casos_validos = []
    for i, caso in enumerate(casos):
        if (
            not isinstance(caso, dict)
            or not isinstance(caso.get("entrada"), str)
            or not isinstance(caso.get("saida_esperada"), str)
        ):
            errors.append(f"{prefix}.casos_de_teste[{i}] precisa de entrada e saida_esperada")
            continue
        casos_validos.append({"entrada": caso["entrada"], "saida_esperada": caso["saida_esperada"]})
    campos["casos_de_teste"] = casos_validos
    return campos


VALIDADORES_POR_TIPO = {
    "multipla_escolha": _validate_multipla_escolha,
    "dissertativa": _validate_dissertativa,
    "desafio_codigo": _validate_desafio_codigo,
}


def _validate_questoes(questoes, errors):
    if not isinstance(questoes, list) or not questoes:
        errors.append("questoes deve ser uma lista com pelo menos uma questão")
        return []

    ids = set()
    validas = []
    for indice, questao in enumerate(questoes):
        prefix = f"questoes[{indice}]"
        if not isinstance(questao, dict):
            errors.append(f"{prefix} deve ser um objeto")
            continue

        id_questao = questao.get("id_questao")
        if not _non_empty_str(id_questao):
            errors.append(f"{prefix}.id_questao é obrigatório")
        elif id_questao in ids:
            errors.append(f"{prefix}.id_questao '{id_questao}' está duplicado")
        else:
            ids.add(id_questao)

        tipo = questao.get("tipo")
        if tipo not in TIPOS_QUESTAO:
            errors.append(f"{prefix}.tipo deve ser um de: {', '.join(TIPOS_QUESTAO)}")
            continue

        if not _non_empty_str(questao.get("enunciado")):
            errors.append(f"{prefix}.enunciado é obrigatório")

        peso = questao.get("peso")
        if not _is_positive_number(peso):
            errors.append(f"{prefix}.peso deve ser um número maior que zero")

        ordem = questao.get("ordem", indice + 1)
        if not _is_int(ordem):
            errors.append(f"{prefix}.ordem deve ser um inteiro")

        validas.append({
            "id_questao": id_questao,
            "ordem": ordem,
            "tipo": tipo,
            "peso": float(peso) if _is_positive_number(peso) else peso,
            "enunciado": questao.get("enunciado"),
            **VALIDADORES_POR_TIPO[tipo](questao, prefix, errors),
        })

    if not errors:
        validas.sort(key=lambda q: q["ordem"])
    return validas


def _validate_configuracoes(config, errors):
    if not isinstance(config, dict):
        errors.append("configuracoes_teste deve ser um objeto")
        return {}

    tempo = config.get("tempo_limite_minutos")
    if tempo is not None and not (_is_int(tempo) and tempo > 0):
        errors.append("configuracoes_teste.tempo_limite_minutos deve ser um inteiro positivo")

    nota_maxima = config.get("nota_maxima", 10.0)
    if not _is_positive_number(nota_maxima):
        errors.append("configuracoes_teste.nota_maxima deve ser um número maior que zero")

    permite_refazer = config.get("permite_refazer", True)
    if not isinstance(permite_refazer, bool):
        errors.append("configuracoes_teste.permite_refazer deve ser true ou false")

    return {
        "tempo_limite_minutos": tempo,
        "nota_maxima": float(nota_maxima) if _is_positive_number(nota_maxima) else nota_maxima,
        "permite_refazer": permite_refazer,
    }


def validate_exam_payload(data) -> dict:
    """Valida o corpo enviado pelo admin e retorna apenas os campos conhecidos."""
    if not isinstance(data, dict):
        raise ExamValidationError(["o corpo da requisição deve ser um objeto JSON"])

    errors = []

    titulo = data.get("titulo")
    if not _non_empty_str(titulo):
        errors.append("titulo é obrigatório")

    status = data.get("status", "RASCUNHO")
    if status not in STATUS_VALIDOS:
        errors.append(f"status deve ser um de: {', '.join(STATUS_VALIDOS)}")

    contexto = data.get("contexto") or {}
    if not isinstance(contexto, dict):
        errors.append("contexto deve ser um objeto")
        contexto = {}

    assunto = contexto.get("assunto_materia")
    if not _non_empty_str(assunto):
        errors.append("contexto.assunto_materia é obrigatório")

    gerado_com_ia = contexto.get("gerado_com_ia")
    if gerado_com_ia is not None and not isinstance(gerado_com_ia, dict):
        errors.append("contexto.gerado_com_ia deve ser um objeto")

    configuracoes = _validate_configuracoes(data.get("configuracoes_teste") or {}, errors)
    questoes = _validate_questoes(data.get("questoes"), errors)

    if errors:
        raise ExamValidationError(errors)

    contexto_validado = {"assunto_materia": assunto.strip()}
    if gerado_com_ia is not None:
        contexto_validado["gerado_com_ia"] = gerado_com_ia

    return {
        "titulo": titulo.strip(),
        "status": status,
        "contexto": contexto_validado,
        "configuracoes_teste": configuracoes,
        "questoes": questoes,
        "total_questoes": len(questoes),
    }


def build_exam_document(exam_id, campos, criado_por, data_criacao, atualizado_por):
    """Monta o documento final, com os metadados preenchidos pelo servidor."""
    contexto = {
        **campos["contexto"],
        "criado_por": {"usuario_id": criado_por},
        "data_criacao": data_criacao,
        "atualizado_por": {"usuario_id": atualizado_por},
        "data_atualizacao": _now(),
    }
    return {"_id": exam_id, **campos, "contexto": contexto}


# ---------------------------------------------------------------------------
# CRUD de provas
# ---------------------------------------------------------------------------

def _can_view(exam, admin):
    return admin or exam.get("status") == STATUS_PUBLICADO


def hide_answer_key(exam: dict) -> dict:
    questoes = [
        {campo: valor for campo, valor in questao.items() if campo not in CAMPOS_GABARITO}
        for questao in exam.get("questoes", [])
    ]
    return {**exam, "questoes": questoes}


def list_exams(admin: bool, assunto: str = None, status: str = None) -> list:
    filters = {}
    if not admin:
        filters["status"] = STATUS_PUBLICADO
    elif status:
        filters["status"] = status
    if assunto:
        filters["contexto.assunto_materia"] = assunto
    return exam_model.list_exams(filters)


def get_exam(exam_id: str, admin: bool):
    exam = exam_model.get_exam(exam_id)
    if not exam or not _can_view(exam, admin):
        return None
    return exam if admin else hide_answer_key(exam)


def create_exam(user_id: str, data) -> dict:
    campos = validate_exam_payload(data)
    exam = build_exam_document(
        f"prova_{uuid4().hex[:12]}", campos, user_id, _now(), user_id
    )
    exam_model.insert_exam(exam)
    return exam


def update_exam(exam_id: str, user_id: str, data):
    campos = validate_exam_payload(data)
    atual = exam_model.get_exam(exam_id)
    if not atual:
        return None

    contexto_atual = atual.get("contexto", {})
    exam = build_exam_document(
        exam_id,
        campos,
        (contexto_atual.get("criado_por") or {}).get("usuario_id"),
        contexto_atual.get("data_criacao"),
        user_id,
    )
    if not exam_model.replace_exam(exam):
        return None
    return exam


def delete_exam(exam_id: str) -> bool:
    # As respostas já enviadas são mantidas para o histórico de desempenho
    return exam_model.delete_exam(exam_id)


# ---------------------------------------------------------------------------
# Respostas e correção
# ---------------------------------------------------------------------------

def _grade_question(questao, resposta, errors):
    item = {
        "id_questao": questao["id_questao"],
        "tipo": questao["tipo"],
        "peso": questao["peso"],
        "resposta": resposta,
    }

    if resposta is None:
        return {**item, "correta": False, "pontos_obtidos": 0.0, "status_correcao": "em_branco"}

    if questao["tipo"] == "multipla_escolha":
        if resposta not in {opcao["id"] for opcao in questao["opcoes"]}:
            errors.append(
                f"resposta da questão '{questao['id_questao']}' deve ser o id de uma das opções"
            )
        correta = resposta == questao["resposta_correta_id"]
        return {
            **item,
            "correta": correta,
            "pontos_obtidos": questao["peso"] if correta else 0.0,
            "status_correcao": "corrigida",
            "resposta_correta_id": questao["resposta_correta_id"],
            "explicacao_gabarito": questao.get("explicacao_gabarito"),
        }

    limite = questao.get("limite_caracteres")
    if limite and len(resposta) > limite:
        errors.append(
            f"resposta da questão '{questao['id_questao']}' excede {limite} caracteres"
        )

    # Dissertativas e desafios de código ficam para correção manual (ou por IA)
    return {**item, "correta": None, "pontos_obtidos": None, "status_correcao": "pendente"}


def grade_answers(exam: dict, data) -> dict:
    if not isinstance(data, dict) or not isinstance(data.get("respostas"), list):
        raise ExamValidationError(["respostas deve ser uma lista"])

    questoes = {questao["id_questao"]: questao for questao in exam.get("questoes", [])}
    errors = []
    enviadas = {}

    for i, item in enumerate(data["respostas"]):
        prefix = f"respostas[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} deve ser um objeto")
            continue
        id_questao = item.get("id_questao")
        if id_questao not in questoes:
            errors.append(f"{prefix}.id_questao '{id_questao}' não existe nesta prova")
            continue
        if id_questao in enviadas:
            errors.append(f"{prefix}.id_questao '{id_questao}' foi respondida mais de uma vez")
            continue
        resposta = item.get("resposta")
        if resposta is not None and not isinstance(resposta, str):
            errors.append(f"{prefix}.resposta deve ser texto")
            continue
        # Texto vazio conta como questão em branco
        enviadas[id_questao] = resposta.strip() if resposta and resposta.strip() else None

    tempo = data.get("tempo_gasto_segundos")
    if tempo is not None and not (_is_int(tempo) and tempo >= 0):
        errors.append("tempo_gasto_segundos deve ser um inteiro maior ou igual a zero")

    corrigidas = [
        _grade_question(questao, enviadas.get(questao["id_questao"]), errors)
        for questao in exam.get("questoes", [])
    ]

    if errors:
        raise ExamValidationError(errors)

    pontos_possiveis = sum(questao["peso"] for questao in exam.get("questoes", []))
    pontos_obtidos = sum(item["pontos_obtidos"] or 0 for item in corrigidas)
    nota_maxima = exam.get("configuracoes_teste", {}).get("nota_maxima", 10.0)
    pendentes = sum(1 for item in corrigidas if item["status_correcao"] == "pendente")

    return {
        "tempo_gasto_segundos": tempo,
        "respostas": corrigidas,
        "resultado": {
            "acertos": sum(1 for item in corrigidas if item["correta"] is True),
            "total_questoes": len(corrigidas),
            "pontos_obtidos": round(pontos_obtidos, 2),
            "pontos_possiveis": round(pontos_possiveis, 2),
            "nota_obtida": (
                round(nota_maxima * pontos_obtidos / pontos_possiveis, 2)
                if pontos_possiveis else 0.0
            ),
            "nota_maxima": nota_maxima,
            "questoes_pendentes_correcao": pendentes,
            "correcao_concluida": pendentes == 0,
        },
    }


def submit_answers(exam_id: str, user_id: str, admin: bool, data):
    exam = exam_model.get_exam(exam_id)
    if not exam or not _can_view(exam, admin):
        return None

    correcao = grade_answers(exam, data)

    tentativas = exam_model.count_attempts(exam_id, user_id)
    if tentativas and not exam.get("configuracoes_teste", {}).get("permite_refazer", True):
        raise ExamConflictError("Esta prova não permite refazer")

    answer = {
        "_id": f"resp_{uuid4().hex[:12]}",
        "prova_id": exam_id,
        "usuario_id": user_id,
        "tentativa": tentativas + 1,
        "titulo_prova": exam.get("titulo"),
        "assunto_materia": exam.get("contexto", {}).get("assunto_materia"),
        "enviado_em": _now(),
        **correcao,
    }

    try:
        exam_model.insert_answer(answer)
    except DuplicateKeyError as error:
        raise ExamConflictError("Tentativa enviada em duplicidade; tente novamente") from error

    return answer


def list_user_answers(user_id: str, exam_id: str = None) -> list:
    if exam_id:
        return exam_model.list_answers({"usuario_id": user_id, "prova_id": exam_id})
    # Histórico geral: só o resultado de cada tentativa, sem as respostas
    return exam_model.list_answers({"usuario_id": user_id}, include_details=False)


def list_exam_answers(exam_id: str) -> list:
    return exam_model.list_answers({"prova_id": exam_id}, include_details=False)
