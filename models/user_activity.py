from datetime import datetime, timezone

from pymongo import DESCENDING

from models.mongo_connection import user_activity_collection, user_activity_days_collection


def mark_active(user_id: str, day: str):
    """Registra que o usuário usou o app no dia (YYYY-MM-DD, fuso local)."""
    agora = datetime.now(timezone.utc)
    user_activity_collection.update_one(
        {"user_id": user_id},
        {"$set": {"last_active_date": day, "last_active_at": agora}},
        upsert=True,
    )
    user_activity_days_collection.update_one(
        {"user_id": user_id, "day": day},
        {"$setOnInsert": {"first_seen_at": agora}},
        upsert=True,
    )


def list_active_days(user_id: str, since_day: str) -> list:
    """Dias de uso (YYYY-MM-DD) a partir de since_day, mais recentes primeiro."""
    return [
        doc["day"]
        for doc in user_activity_days_collection.find(
            {"user_id": user_id, "day": {"$gte": since_day}},
            {"_id": 0, "day": 1},
        ).sort("day", DESCENDING)
    ]
