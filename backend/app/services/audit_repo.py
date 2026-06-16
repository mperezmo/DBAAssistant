# backend/app/services/audit_repo.py
"""Bitácora de auditoría en MongoDB (Sprint 4).

Registra quién hizo qué y cuándo. Escribir auditoría NUNCA debe romper la acción
principal: log() captura cualquier error.
"""
from datetime import datetime, timezone

from app.config import get_settings
from app.services.db import mongo_client

settings = get_settings()
_col = mongo_client[settings.mongodb_database]["audit_log"]


def log(user: str, action: str, target: str | None = None,
        detail: str | None = None, ip: str | None = None) -> None:
    try:
        _col.insert_one({
            "ts": datetime.now(timezone.utc),
            "user": user,
            "action": action,
            "target": target,
            "detail": detail,
            "ip": ip,
        })
    except Exception:
        pass


def _public(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "timestamp": doc["ts"].isoformat(),
        "user": doc.get("user"),
        "action": doc.get("action"),
        "target": doc.get("target"),
        "detail": doc.get("detail"),
        "ip": doc.get("ip"),
    }


def list_recent(limit: int = 100, action: str | None = None) -> list[dict]:
    query = {"action": action} if action else {}
    docs = _col.find(query).sort("ts", -1).limit(limit)
    return [_public(d) for d in docs]
