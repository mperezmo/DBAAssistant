# tests/unit/test_alerts.py
"""Tests de Alertas (Sprint 11): reglas, feed, acciones y motor de evaluación.

Repos y resolución de métricas mockeados (no tocan DMVs ni Mongo reales).
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from bson import ObjectId

CONN = "650000000000000000000001"
DB = "DBAAssistant"


def _auth(client):
    res = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


RULE = {"id": "r1", "name": "CPU alta", "connection_id": CONN, "database": "",
        "metric": "cpu_percent", "operator": "gt", "threshold": 85.0, "severity": "critical",
        "suggested_workaround_key": None, "auto_remediate": False, "auto_threshold": None,
        "cooldown_seconds": 300, "enabled": True, "last_checked": None, "last_value": None,
        "last_triggered": None}


# ── Reglas / plantillas ──────────────────────────────────────────────────────

def test_rules_requires_auth(client):
    assert client.get("/alerts/rules").status_code == 401


def test_templates_lists_presets(client):
    res = client.get("/alerts/templates", headers=_auth(client))
    assert res.status_code == 200
    metrics = {t["metric"] for t in res.json()}
    assert {"cpu_percent", "log_used_pct", "service_down"} <= metrics


def test_create_rule_ok(client):
    body = {"name": "CPU alta", "connection_id": CONN, "metric": "cpu_percent",
            "operator": "gt", "threshold": 85, "severity": "critical"}
    with patch("app.services.alerts_repo.create_rule", return_value=RULE) as mock_create, \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.post("/alerts/rules", json=body, headers=_auth(client))
    assert res.status_code == 201
    mock_create.assert_called_once()
    assert mock_audit.call_args.args[1] == "alert.rule_create"


def test_create_rule_invalid_metric_400(client):
    body = {"name": "x", "connection_id": CONN, "metric": "nope", "threshold": 1}
    res = client.post("/alerts/rules", json=body, headers=_auth(client))
    assert res.status_code == 400


def test_create_rule_bad_workaround_400(client):
    body = {"name": "x", "connection_id": CONN, "metric": "cpu_percent", "threshold": 85,
            "suggested_workaround_key": "ghost"}
    with patch("app.services.workaround_exec.resolve", return_value=None):
        res = client.post("/alerts/rules", json=body, headers=_auth(client))
    assert res.status_code == 400


def test_seed_rules_creates_recommended(client):
    with patch("app.services.alerts_repo.has_rule_for_metric", return_value=False), \
         patch("app.services.alerts_repo.create_rule", side_effect=lambda d: {**RULE, **d, "id": "x"}), \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.post(f"/alerts/rules/seed?connection_id={CONN}", headers=_auth(client))
    assert res.status_code == 201
    # sin `database`, no se seedea la regla por base (log_used_pct)
    metrics = {r["metric"] for r in res.json()}
    assert "cpu_percent" in metrics and "log_used_pct" not in metrics
    assert mock_audit.call_args.args[1] == "alert.rule_seed"


def test_update_rule_ok(client):
    with patch("app.services.alerts_repo.update_rule", return_value={**RULE, "enabled": False}), \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.put("/alerts/rules/r1", json={"enabled": False}, headers=_auth(client))
    assert res.status_code == 200 and res.json()["enabled"] is False
    assert mock_audit.call_args.args[1] == "alert.rule_update"


def test_update_rule_404(client):
    with patch("app.services.alerts_repo.update_rule", return_value=None):
        res = client.put("/alerts/rules/ghost", json={"enabled": False}, headers=_auth(client))
    assert res.status_code == 404


def test_delete_rule_ok_and_404(client):
    with patch("app.services.alerts_repo.delete_rule", return_value=True), \
         patch("app.services.audit_repo.log"):
        assert client.delete("/alerts/rules/r1", headers=_auth(client)).status_code == 204
    with patch("app.services.alerts_repo.delete_rule", return_value=False):
        assert client.delete("/alerts/rules/ghost", headers=_auth(client)).status_code == 404


# ── Feed de alertas ──────────────────────────────────────────────────────────

ALERT = {"id": "a1", "rule_id": "r1", "connection_id": CONN, "source": "Mi SQL",
         "metric": "cpu_percent", "value": 91.0, "threshold": 85.0, "severity": "critical",
         "title": "CPU % > 85", "description": "Valor 91.", "status": "active",
         "suggested_workaround_key": "kill_blocking_sessions", "auto_remediated": False,
         "assigned_to": None, "created_at": "2026-06-22T14:00:00+00:00",
         "updated_at": "2026-06-22T14:00:00+00:00"}


def test_list_alerts(client):
    with patch("app.services.alerts_repo.list_alerts", return_value=[ALERT]):
        res = client.get("/alerts", headers=_auth(client))
    assert res.status_code == 200 and res.json()[0]["severity"] == "critical"


def test_count_active(client):
    with patch("app.services.alerts_repo.count_active", return_value=3):
        res = client.get("/alerts/count", headers=_auth(client))
    assert res.status_code == 200 and res.json()["active"] == 3


def test_patch_alert_ok(client):
    with patch("app.services.alerts_repo.set_status", return_value={**ALERT, "status": "resolved"}), \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.patch("/alerts/a1", json={"status": "resolved"}, headers=_auth(client))
    assert res.status_code == 200 and res.json()["status"] == "resolved"
    assert mock_audit.call_args.args[1] == "alert.update"


def test_patch_alert_invalid_status_400(client):
    res = client.patch("/alerts/a1", json={"status": "weird"}, headers=_auth(client))
    assert res.status_code == 400


def test_patch_alert_404(client):
    with patch("app.services.alerts_repo.set_status", return_value=None):
        res = client.patch("/alerts/ghost", json={"status": "resolved"}, headers=_auth(client))
    assert res.status_code == 404


def test_evaluate_endpoint_audits(client):
    fake = [{"rule_id": "r1", "name": "CPU alta", "metric": "cpu_percent",
             "checked": True, "breached": True, "value": 91.0, "auto_remediated": False}]
    with patch("app.services.alerts.evaluate", return_value=fake) as mock_eval, \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.post("/alerts/evaluate", headers=_auth(client))
    assert res.status_code == 200 and res.json()[0]["breached"] is True
    mock_eval.assert_called_once()
    assert mock_audit.call_args.args[1] == "alert.evaluate"


# ── Motor de evaluación (alerts.evaluate) ────────────────────────────────────

def _raw(**over):
    base = {"_id": ObjectId(), "name": "r", "metric": "cpu_percent", "connection_id": CONN,
            "database": "", "operator": "gt", "threshold": 85.0, "severity": "critical",
            "suggested_workaround_key": None, "auto_remediate": False, "auto_threshold": None,
            "cooldown_seconds": 300, "last_triggered": None}
    base.update(over)
    return base


def test_engine_raises_alert_on_breach():
    from app.services import alerts
    with patch("app.services.alerts_repo.list_enabled_rules_raw", return_value=[_raw()]), \
         patch("app.services.connections_repo.list_all", return_value=[]), \
         patch("app.services.alerts._metric_value", return_value=91.0), \
         patch("app.services.alerts_repo.raise_or_update", return_value={"id": "a1"}) as mock_raise, \
         patch("app.services.alerts_repo.mark_checked"):
        out = alerts.evaluate("tester")
    assert out[0]["breached"] is True and out[0]["value"] == 91.0
    mock_raise.assert_called_once()


def test_engine_auto_remediates_at_max():
    from app.services import alerts
    raw = _raw(metric="log_used_pct", database=DB, operator="gt", threshold=80.0,
               suggested_workaround_key="shrink_log", auto_remediate=True, auto_threshold=99.0)
    apply_mock = MagicMock(return_value="ok")
    with patch("app.services.alerts_repo.list_enabled_rules_raw", return_value=[raw]), \
         patch("app.services.connections_repo.list_all", return_value=[]), \
         patch("app.services.alerts._metric_value", return_value=99.5), \
         patch("app.services.alerts_repo.raise_or_update", return_value={"id": "a1"}), \
         patch("app.services.alerts_repo.mark_auto_remediated") as mock_mar, \
         patch("app.services.alerts_repo.mark_checked"), \
         patch("app.services.workaround_exec.resolve", return_value={"key": "shrink_log", "kind": "sql"}), \
         patch("app.services.workaround_exec.apply", apply_mock), \
         patch("app.services.workarounds_repo.log_run"), \
         patch("app.services.audit_repo.log") as mock_audit:
        out = alerts.evaluate("tester")
    assert out[0]["auto_remediated"] is True
    apply_mock.assert_called_once()
    mock_mar.assert_called_once()
    assert mock_audit.call_args.args[1] == "alert.auto_remediate"


def test_engine_auto_remediates_after_duration():
    """Servicio caído por más de N seg → auto-inicia (disparo por duración)."""
    from app.services import alerts
    raw = _raw(metric="service_down", operator="gte", threshold=1.0,
               suggested_workaround_key="start_sql_service", auto_remediate=True,
               auto_threshold=None, auto_after_seconds=60)
    old = {"id": "a1", "created_at": (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()}
    apply_mock = MagicMock(return_value="ok")
    with patch("app.services.alerts_repo.list_enabled_rules_raw", return_value=[raw]), \
         patch("app.services.connections_repo.list_all", return_value=[]), \
         patch("app.services.alerts._metric_value", return_value=1.0), \
         patch("app.services.alerts_repo.raise_or_update", return_value=old), \
         patch("app.services.alerts_repo.mark_auto_remediated"), \
         patch("app.services.alerts_repo.mark_checked"), \
         patch("app.services.workaround_exec.resolve", return_value={"key": "start_sql_service", "kind": "service"}), \
         patch("app.services.workaround_exec.apply", apply_mock), \
         patch("app.services.workarounds_repo.log_run"), \
         patch("app.services.audit_repo.log") as mock_audit:
        out = alerts.evaluate("tester")
    assert out[0]["auto_remediated"] is True
    apply_mock.assert_called_once()
    assert mock_audit.call_args.args[1] == "alert.auto_remediate"


def test_engine_auto_waits_until_duration_met():
    """Recién caído (no llegó a N seg) → alerta sí, pero NO auto-remedia todavía."""
    from app.services import alerts
    raw = _raw(metric="service_down", operator="gte", threshold=1.0,
               suggested_workaround_key="start_sql_service", auto_remediate=True,
               auto_threshold=None, auto_after_seconds=300)
    fresh = {"id": "a1", "created_at": datetime.now(timezone.utc).isoformat()}
    apply_mock = MagicMock()
    with patch("app.services.alerts_repo.list_enabled_rules_raw", return_value=[raw]), \
         patch("app.services.connections_repo.list_all", return_value=[]), \
         patch("app.services.alerts._metric_value", return_value=1.0), \
         patch("app.services.alerts_repo.raise_or_update", return_value=fresh), \
         patch("app.services.alerts_repo.mark_checked"), \
         patch("app.services.workaround_exec.apply", apply_mock), \
         patch("app.services.audit_repo.log"):
        out = alerts.evaluate("tester")
    assert out[0]["breached"] is True and out[0]["auto_remediated"] is False
    assert "sostenida" in (out[0]["status"] or "")
    apply_mock.assert_not_called()


def test_engine_auto_skipped_in_cooldown():
    from app.services import alerts
    raw = _raw(metric="blocked", operator="gt", threshold=0.0, suggested_workaround_key="kill_blocking_sessions",
               auto_remediate=True, auto_threshold=5.0, last_triggered=datetime.now(timezone.utc))
    apply_mock = MagicMock()
    with patch("app.services.alerts_repo.list_enabled_rules_raw", return_value=[raw]), \
         patch("app.services.connections_repo.list_all", return_value=[]), \
         patch("app.services.alerts._metric_value", return_value=8.0), \
         patch("app.services.alerts_repo.raise_or_update", return_value={"id": "a1"}), \
         patch("app.services.alerts_repo.mark_checked"), \
         patch("app.services.workaround_exec.apply", apply_mock), \
         patch("app.services.audit_repo.log"):
        out = alerts.evaluate("tester")
    assert out[0]["breached"] is True and out[0]["auto_remediated"] is False
    apply_mock.assert_not_called()


def test_engine_resolves_when_cleared():
    from app.services import alerts
    with patch("app.services.alerts_repo.list_enabled_rules_raw", return_value=[_raw()]), \
         patch("app.services.connections_repo.list_all", return_value=[]), \
         patch("app.services.alerts._metric_value", return_value=10.0), \
         patch("app.services.alerts_repo.resolve_active_for_rule") as mock_resolve, \
         patch("app.services.alerts_repo.mark_checked"):
        out = alerts.evaluate("tester")
    assert out[0]["breached"] is False
    mock_resolve.assert_called_once()


def test_engine_metric_unavailable_skips():
    from app.services import alerts
    with patch("app.services.alerts_repo.list_enabled_rules_raw", return_value=[_raw()]), \
         patch("app.services.connections_repo.list_all", return_value=[]), \
         patch("app.services.alerts._metric_value", return_value=None), \
         patch("app.services.alerts_repo.mark_checked"):
        out = alerts.evaluate("tester")
    assert out[0]["checked"] is False and out[0]["breached"] is False
