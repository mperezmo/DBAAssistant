# backend/app/services/workarounds_repo.py
"""Persistencia de Workarounds en MongoDB (Sprint 10).

Dos colecciones:
- ``workarounds``: workarounds CUSTOM creados por el usuario (los built-in viven
  en código, en ``services/workarounds.py``).
- ``workaround_runs``: bitácora de ejecuciones (diagnóstico/aplicar) que alimenta
  las estadísticas de cada tarjeta (ejecuciones · última corrida).
"""
from datetime import datetime, timezone

from app.config import get_settings
from app.services.db import mongo_client

settings = get_settings()
_col = mongo_client[settings.mongodb_database]["workarounds"]
_runs = mongo_client[settings.mongodb_database]["workaround_runs"]


# ── Workarounds custom ───────────────────────────────────────────────────────

def _public(doc: dict) -> dict:
    return {
        "key": doc["key"],
        "name": doc.get("name", doc["key"]),
        "description": doc.get("description", ""),
        "category": doc.get("category", "Mantenimiento"),
        "severity": doc.get("severity", "info"),
        "requires_server_state": doc.get("requires_server_state", False),
        "builtin": False,
        "diagnose_sql": doc.get("diagnose_sql"),
        "apply_sql": doc.get("apply_sql"),
    }


def list_custom() -> list[dict]:
    return [_public(d) for d in _col.find().sort("created_at", 1)]


def get_custom(key: str) -> dict | None:
    doc = _col.find_one({"key": key})
    return _public(doc) if doc else None


def create_custom(data: dict) -> dict:
    doc = {**data, "created_at": datetime.now(timezone.utc)}
    _col.update_one({"key": data["key"]}, {"$set": doc}, upsert=True)
    return _public(doc)


def delete_custom(key: str) -> bool:
    return _col.delete_one({"key": key}).deleted_count > 0


# ── Bitácora de ejecuciones ──────────────────────────────────────────────────

def log_run(user: str, key: str, connection_id: str, database: str, mode: str,
            success: bool, affected: int | None = None, error: str | None = None) -> None:
    try:
        _runs.insert_one({
            "ts": datetime.now(timezone.utc),
            "user": user,
            "key": key,
            "connection_id": connection_id,
            "database": database,
            "mode": mode,
            "success": success,
            "affected_rows": affected,
            "error": error,
        })
    except Exception:
        pass


def run_stats() -> dict[str, dict]:
    """Por workaround: cantidad de ejecuciones y timestamp de la última (ISO)."""
    stats: dict[str, dict] = {}
    try:
        cursor = _runs.aggregate([
            {"$group": {"_id": "$key", "runs": {"$sum": 1}, "last": {"$max": "$ts"}}},
        ])
        for row in cursor:
            last = row.get("last")
            stats[row["_id"]] = {
                "runs": row.get("runs", 0),
                "last_run": last.isoformat() if last else None,
            }
    except Exception:
        pass
    return stats


def list_runs(limit: int = 50) -> list[dict]:
    out = []
    for d in _runs.find().sort("ts", -1).limit(limit):
        out.append({
            "id": str(d["_id"]),
            "timestamp": d["ts"].isoformat(),
            "user": d.get("user"),
            "key": d.get("key"),
            "connection_id": d.get("connection_id"),
            "database": d.get("database"),
            "mode": d.get("mode"),
            "success": d.get("success", True),
            "affected_rows": d.get("affected_rows"),
            "error": d.get("error"),
        })
    return out
