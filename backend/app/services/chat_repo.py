# backend/app/services/chat_repo.py
"""Persistencia del historial de chat en MongoDB (Sprint 3).

Cada documento de la colección `conversations`:
  { _id, user, title, created_at, updated_at,
    messages: [ {role, content, ts}, ... ] }
"""
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from app.config import get_settings
from app.services.db import mongo_client

settings = get_settings()
_db = mongo_client[settings.mongodb_database]
_conversations = _db["conversations"]


def _oid(conversation_id: str) -> ObjectId | None:
    try:
        return ObjectId(conversation_id)
    except (InvalidId, TypeError):
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


def create_conversation(user: str, title: str) -> str:
    res = _conversations.insert_one(
        {"user": user, "title": title, "created_at": _now(),
         "updated_at": _now(), "messages": []}
    )
    return str(res.inserted_id)


def add_message(conversation_id: str, role: str, content: str) -> None:
    oid = _oid(conversation_id)
    if not oid:
        return
    _conversations.update_one(
        {"_id": oid},
        {"$push": {"messages": {"role": role, "content": content, "ts": _now()}},
         "$set": {"updated_at": _now()}},
    )


def get_history(conversation_id: str, user: str) -> list[dict]:
    """Devuelve [{role, content}, ...] para enviar a Claude."""
    oid = _oid(conversation_id)
    if not oid:
        return []
    doc = _conversations.find_one({"_id": oid, "user": user})
    if not doc:
        return []
    return [{"role": m["role"], "content": m["content"]} for m in doc.get("messages", [])]


def get_conversation(conversation_id: str, user: str) -> dict | None:
    oid = _oid(conversation_id)
    if not oid:
        return None
    doc = _conversations.find_one({"_id": oid, "user": user})
    return _serialize(doc) if doc else None


def list_conversations(user: str) -> list[dict]:
    docs = (
        _conversations.find({"user": user}, {"messages": 0})
        .sort("updated_at", -1)
    )
    return [_serialize(d) for d in docs]
