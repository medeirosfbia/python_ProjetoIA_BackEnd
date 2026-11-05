import functools
import logging
import re

from messaging.queue_notification_producer import TODOS_USUARIOS, publicar_notificacao
from models import push_token as push_token_model

PLATAFORMAS_VALIDAS = ("android", "ios")
TOKEN_REGEX = re.compile(r"^Expo(nent)?PushToken\[[^\]\s]{1,200}\]$")
TITULO_MAX = 100
CORPO_MAX = 500
DESTINATARIOS_MAX = 500

logger = logging.getLogger(__name__)


class NotificationValidationError(ValueError):
    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


def _non_empty_str(value):
    return isinstance(value, str) and bool(value.strip())


def _validate_token(data, errors):
    token = data.get("token")
    if not (isinstance(token, str) and TOKEN_REGEX.match(token)):
        errors.append("token deve ser um ExpoPushToken válido")
    return token


# ---------------------------------------------------------------------------
# Cadastro dos aparelhos (feito pelo app após login / antes do logout)
# ---------------------------------------------------------------------------

def register_token(user_id: str, data) -> dict:
    if not isinstance(data, dict):
        raise NotificationValidationError(["O corpo da requisição deve ser um objeto JSON"])

    errors = []
    token = _validate_token(data, errors)
    platform = data.get("platform")
    if platform not in PLATAFORMAS_VALIDAS:
        errors.append(f"platform deve ser um de: {', '.join(PLATAFORMAS_VALIDAS)}")
    if errors:
        raise NotificationValidationError(errors)

    push_token_model.save_token(user_id, token, platform)
    return {"token": token, "platform": platform}


def unregister_token(user_id: str, data) -> bool:
    if not isinstance(data, dict):
        raise NotificationValidationError(["O corpo da requisição deve ser um objeto JSON"])

    errors = []
    token = _validate_token(data, errors)
    if errors:
        raise NotificationValidationError(errors)

    return push_token_model.delete_token(user_id, token)


# ---------------------------------------------------------------------------
# Envio (publica na fila; a Azure Function entrega via Expo)
# ---------------------------------------------------------------------------

def validate_send_payload(data) -> dict:
    if not isinstance(data, dict):
        raise NotificationValidationError(["O corpo da requisição deve ser um objeto JSON"])

    errors = []
    titulo = data.get("title")
    if not (_non_empty_str(titulo) and len(titulo) <= TITULO_MAX):
        errors.append(f"title é obrigatório e deve ter até {TITULO_MAX} caracteres")

    corpo = data.get("body")
    if not (_non_empty_str(corpo) and len(corpo) <= CORPO_MAX):
        errors.append(f"body é obrigatório e deve ter até {CORPO_MAX} caracteres")

    destinatarios = data.get("recipients", TODOS_USUARIOS)
    if destinatarios != TODOS_USUARIOS and not (
        isinstance(destinatarios, list)
        and 0 < len(destinatarios) <= DESTINATARIOS_MAX
        and all(_non_empty_str(user_id) for user_id in destinatarios)
    ):
        errors.append(
            f'recipients deve ser "{TODOS_USUARIOS}" ou uma lista de '
            f"1 a {DESTINATARIOS_MAX} usuários"
        )

    dados = data.get("data", {})
    if not isinstance(dados, dict):
        errors.append("data deve ser um objeto")

    if errors:
        raise NotificationValidationError(errors)

    if isinstance(destinatarios, list):
        destinatarios = sorted({user_id.strip() for user_id in destinatarios})

    return {
        "titulo": titulo.strip(),
        "corpo": corpo.strip(),
        "destinatarios": destinatarios,
        "dados": dados,
    }


def send_custom_notification(data) -> str:
    """Notificação avulsa enviada por um admin. Erros da fila sobem para o controller."""
    campos = validate_send_payload(data)
    return publicar_notificacao("custom", **campos)


def _never_raises(notify):
    # A notificação é secundária: nenhuma falha pode desfazer a operação principal
    @functools.wraps(notify)
    def wrapper(*args, **kwargs):
        try:
            notify(*args, **kwargs)
        except Exception:
            logger.exception("Falha ao publicar notificação em %s", notify.__name__)
    return wrapper


@_never_raises
def notify_exam_published(exam: dict):
    assunto = exam.get("contexto", {}).get("assunto_materia")
    corpo = exam.get("titulo") or "Uma nova prova está disponível."
    if assunto:
        corpo = f"{corpo} ({assunto})"
    publicar_notificacao(
        "exam_published",
        "Nova prova disponível",
        corpo,
        dados={"examId": exam["_id"]},
    )


@_never_raises
def notify_material_created(material: dict):
    publicar_notificacao(
        "material_created",
        "Novo material de estudo",
        f"{material['nome']} foi adicionado em {material['conteudo']}.",
        dados={"conteudo": material["conteudo"], "nome": material["nome"]},
    )
