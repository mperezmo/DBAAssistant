# backend/app/services/alerts_repo.py
"""Persistencia de Alertas en MongoDB (Sprint 11).

Dos colecciones:
- ``alert_rules``: reglas/umbrales configurados (built-in seedeadas + custom).
- ``alerts``: alertas levantadas, con su ciclo de vida
  (active → acknowledged → resolved | false_alarm).
"""
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from app.config import get_settings
from app.services.db import mongo_client

settings = get_settings()
_rules = mongo_client[settings.mongodb_database]["alert_rules"]
_alerts = mongo_client[settings.mongodb_database]["alerts"]

_SEV_ORDER = {"critical": 0, "warning": 1, "info": 2}
_OPEN = ("active", "acknowledged")


def _oid(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def _iso(v):
    return v.isoformat() if v else None


# ── Reglas ───────────────────────────────────────────────────────────────────

def _rule_public(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name", ""),
        "connection_id": doc.get("connection_id", ""),
        "database": doc.get("database", ""),
        "metric": doc.get("metric"),
        "operator": doc.get("operator", "gt"),
        "threshold": doc.get("threshold"),
        "severity": doc.get("severity", "warning"),
        "suggested_workaround_key": doc.get("suggested_workaround_key"),
        "auto_remediate": doc.get("auto_remediate", False),
        "auto_threshold": doc.get("auto_threshold"),
        "auto_after_seconds": doc.get("auto_after_seconds"),
        "cooldown_seconds": doc.get("cooldown_seconds", 300),
        "enabled": doc.get("enabled", True),
        "last_checked": _iso(doc.get("last_checked")),
        "last_value": doc.get("last_value"),
        "last_triggered": _iso(doc.get("last_triggered")),
    }


def list_rules(connection_id: str | None = None) -> list[dict]:
    query = {"connection_id": connection_id} if connection_id else {}
    return [_rule_public(d) for d in _rules.find(query).sort("created_at", 1)]


def get_rule(rule_id: str) -> dict | None:
    oid = _oid(rule_id)
    doc = _rules.find_one({"_id": oid}) if oid else None
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
    return bool(oid) and _rules.delete_one({"_id": oid}).deleted_count > 0


def has_rule_for_metric(connection_id: str, metric: str, database: str = "") -> bool:
    return _rules.count_documents(
        {"connection_id": connection_id, "metric": metric, "database": database}) > 0


def mark_checked(rule_id: str, value: float | None, remediated: bool) -> None:
    oid = _oid(rule_id)
    if not oid:
        return
    now = datetime.now(timezone.utc)
    fields = {"last_checked": now, "last_value": value}
    if remediated:
        fields["last_triggered"] = now
    try:
        _rules.update_one({"_id": oid}, {"$set": fields})
    except Exception:
        pass


def list_enabled_rules_raw() -> list[dict]:
    """Reglas habilitadas con doc crudo (last_triggered como datetime), para el motor."""
    return list(_rules.find({"enabled": True}))


# ── Alertas ──────────────────────────────────────────────────────────────────

def _alert_public(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "rule_id": doc.get("rule_id"),
        "connection_id": doc.get("connection_id", ""),
        "source": doc.get("source", ""),
        "metric": doc.get("metric"),
        "value": doc.get("value"),
        "threshold": doc.get("threshold"),
        "severity": doc.get("severity", "warning"),
        "title": doc.get("title", ""),
        "description": doc.get("description", ""),
        "status": doc.get("status", "active"),
        "suggested_workaround_key": doc.get("suggested_workaround_key"),
        "auto_remediated": doc.get("auto_remediated", False),
        "assigned_to": doc.get("assigned_to"),
        "created_at": _iso(doc.get("created_at")),
        "updated_at": _iso(doc.get("updated_at")),
    }


def active_for_rule(rule_id: str) -> dict | None:
    doc = _alerts.find_one({"rule_id": rule_id, "status": {"$in": list(_OPEN)}})
    return _alert_public(doc) if doc else None


def raise_or_update(data: dict) -> dict:
    """Dedup: si ya hay una alerta abierta para la regla, la actualiza; si no, crea una."""
    now = datetime.now(timezone.utc)
    existing = _alerts.find_one({"rule_id": data["rule_id"], "status": {"$in": list(_OPEN)}})
    if existing:
        _alerts.update_one(
            {"_id": existing["_id"]},
            {"$set": {"value": data.get("value"), "severity": data.get("severity"),
                      "title": data.get("title"), "description": data.get("description"),
                      "updated_at": now}},
        )
        return _alert_public(_alerts.find_one({"_id": existing["_id"]}))
    doc = {**data, "status": "active", "auto_remediated": False,
           "assigned_to": None, "created_at": now, "updated_at": now}
    res = _alerts.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _alert_public(doc)


def mark_auto_remediated(alert_id: str) -> None:
    oid = _oid(alert_id)
    if oid:
        _alerts.update_one({"_id": oid}, {"$set": {
            "auto_remediated": True, "updated_at": datetime.now(timezone.utc)}})


def resolve_active_for_rule(rule_id: str) -> int:
    """La condición se limpió: resuelve las alertas abiertas de esa regla."""
    res = _alerts.update_many(
        {"rule_id": rule_id, "status": {"$in": list(_OPEN)}},
        {"$set": {"status": "resolved", "updated_at": datetime.now(timezone.utc)}},
    )
    return res.modified_count


def list_alerts(status: str | None = None) -> list[dict]:
    if status:
        query = {"status": status}
    else:
        query = {"status": {"$in": list(_OPEN)}}   # feed por defecto: abiertas
    docs = list(_alerts.find(query))
    docs.sort(key=lambda d: (_SEV_ORDER.get(d.get("severity"), 9),
                             -(d.get("created_at").timestamp() if d.get("created_at") else 0)))
    return [_alert_public(d) for d in docs]


def set_status(alert_id: str, status: str | None, assigned_to: str | None) -> dict | None:
    oid = _oid(alert_id)
    if not oid:
        return None
    fields = {"updated_at": datetime.now(timezone.utc)}
    if status:
        fields["status"] = status
    if assigned_to is not None:
        fields["assigned_to"] = assigned_to
    res = _alerts.update_one({"_id": oid}, {"$set": fields})
    if res.matched_count == 0:
        return None
    return _alert_public(_alerts.find_one({"_id": oid}))


def count_active() -> int:
    return _alerts.count_documents({"status": {"$in": list(_OPEN)}})
