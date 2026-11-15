from datetime import datetime, timezone

from models.mongo_connection import push_tokens_collection


def save_token(user_id: str, token: str, platform: str):
    """Associa o token ao usuário. Se o aparelho trocou de conta, o token passa
    a pertencer ao usuário atual."""
    agora = datetime.now(timezone.utc)
    push_tokens_collection.update_one(
        {"token": token},
        {
            "$set": {"user_id": user_id, "platform": platform, "updated_at": agora},
            "$setOnInsert": {"created_at": agora},
        },
        upsert=True,
    )


def delete_token(user_id: str, token: str) -> bool:
    result = push_tokens_collection.delete_one({"token": token, "user_id": user_id})
    return result.deleted_count == 1
