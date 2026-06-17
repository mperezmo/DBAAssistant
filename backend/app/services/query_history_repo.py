# backend/app/services/query_history_repo.py
"""Historial de queries ejecutadas, en MongoDB (Sprint 5)."""
from datetime import datetime, timezone

from app.config import get_settings
from app.services.db import mongo_client

settings = get_settings()
_col = mongo_client[settings.mongodb_database]["query_history"]


def add(user: str, connection_id: str, database: str, sql: str,
        kind: str | None = None, affected_rows: int | None = None,
        committed: bool = False, success: bool = True, error: str | None = None) -> None:
    try:
        _col.insert_one({
            "ts": datetime.now(timezone.utc),
            "user": user,
            "connection_id": connection_id,
            "database": database,
            "sql": sql[:4000],
            "kind": kind,
            "affected_rows": affected_rows,
            "committed": committed,
            "success": success,
            "error": error,
        })
    except Exception:
        pass


def _public(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "timestamp": doc["ts"].isoformat(),
        "user": doc.get("user"),
        "connection_id": doc.get("connection_id"),
        "database": doc.get("database"),
        "sql": doc.get("sql"),
        "kind": doc.get("kind"),
        "affected_rows": doc.get("affected_rows"),
        "committed": doc.get("committed", False),
        "success": doc.get("success", True),
        "error": doc.get("error"),
    }


def list_recent(limit: int = 50) -> list[dict]:
    return [_public(d) for d in _col.find().sort("ts", -1).limit(limit)]
