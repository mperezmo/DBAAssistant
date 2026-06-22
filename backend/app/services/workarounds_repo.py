# backend/app/services/workarounds_repo.py
"""Persistencia de Workarounds en MongoDB (Sprint 10).

Dos colecciones:
- ``workarounds``: workarounds CUSTOM creados por el usuario (los built-in viven
  en código, en ``services/workarounds.py``).
- ``workaround_runs``: bitácora de ejecuciones (diagnóstico/aplicar) que alimenta
  las estadísticas de cada tarjeta (ejecuciones · última corrida).
"""
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from app.config import get_settings
from app.services.db import mongo_client

settings = get_settings()
_col = mongo_client[settings.mongodb_database]["workarounds"]
_runs = mongo_client[settings.mongodb_database]["workaround_runs"]
_rules = mongo_client[settings.mongodb_database]["workaround_rules"]


def _oid(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


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


# ── Reglas de automatización ─────────────────────────────────────────────────

def _rule_public(doc: dict) -> dict:
    def _iso(v):
        return v.isoformat() if v else None
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name", ""),
        "workaround_key": doc.get("workaround_key", ""),
        "connection_id": doc.get("connection_id", ""),
        "database": doc.get("database", ""),
        "enabled": doc.get("enabled", True),
        "min_rows": doc.get("min_rows", 1),
        "cooldown_seconds": doc.get("cooldown_seconds", 300),
        "last_triggered": _iso(doc.get("last_triggered")),
        "last_checked": _iso(doc.get("last_checked")),
        "last_status": doc.get("last_status"),
    }


def list_rules() -> list[dict]:
    return [_rule_public(d) for d in _rules.find().sort("created_at", 1)]


def get_rule(rule_id: str) -> dict | None:
    oid = _oid(rule_id)
    if not oid:
        return None
    doc = _rules.find_one({"_id": oid})
    return _rule_public(doc) if doc else None


def create_rule(data: dict) -> dict:
    doc = {**data, "created_at": datetime.now(timezone.utc)}
    res = _rules.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _rule_public(doc)


def update_rule(rule_id: str, data: dict) -> dict | None:
    oid = _oid(rule_id)
    if not oid:
        return None
    fields = {k: v for k, v in data.items() if v is not None}
    if fields:
        _rules.update_one({"_id": oid}, {"$set": fields})
    return get_rule(rule_id)


def delete_rule(rule_id: str) -> bool:
    oid = _oid(rule_id)
    if not oid:
        return False
    return _rules.delete_one({"_id": oid}).deleted_count > 0


def mark_checked(rule_id: str, triggered: bool, status: str | None = None) -> None:
    oid = _oid(rule_id)
    if not oid:
        return
    now = datetime.now(timezone.utc)
    fields = {"last_checked": now, "last_status": status}
    if triggered:
        fields["last_triggered"] = now
    try:
        _rules.update_one({"_id": oid}, {"$set": fields})
    except Exception:
        pass


def list_enabled_rules_raw() -> list[dict]:
    """Reglas habilitadas con su doc crudo (incluye last_triggered como datetime),
    para el motor de evaluación (necesita calcular cooldown)."""
    return list(_rules.find({"enabled": True}))
