from datetime import datetime, timezone

from models.mongo_connection import user_activity_collection


def mark_active(user_id: str, day: str):
    """Registra que o usuário usou o app no dia (YYYY-MM-DD, fuso local)."""
    user_activity_collection.update_one(
        {"user_id": user_id},
        {"$set": {"last_active_date": day, "last_active_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
