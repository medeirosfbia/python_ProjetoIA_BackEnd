import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from models import user_activity as user_activity_model

# "Hoje" é contado no fuso dos usuários, igual ao lembrete diário da Function
REMINDER_TIMEZONE = ZoneInfo(os.getenv("REMINDER_TIMEZONE", "America/Sao_Paulo"))

logger = logging.getLogger(__name__)

# Cache por processo: grava no MongoDB só na primeira requisição do dia de cada usuário
_cache_day = None
_cache_users = set()


def local_today() -> str:
    return datetime.now(REMINDER_TIMEZONE).date().isoformat()


def record_activity(user_id: str):
    global _cache_day, _cache_users

    today = local_today()
    if today != _cache_day:
        _cache_day, _cache_users = today, set()
    if user_id in _cache_users:
        return

    # Falha aqui não pode bloquear a requisição: no pior caso o usuário recebe o lembrete
    try:
        user_activity_model.mark_active(user_id, today)
    except Exception:
        logger.exception("Falha ao registrar atividade do usuário")
        return
    _cache_users.add(user_id)
