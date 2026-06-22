# tests/unit/test_automation.py
"""Tests de host-control WinRM y automatización de workarounds (Sprint 10.1).

WinRM se mockea a nivel de funciones de host_control (nunca se importa winrm).
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from bson import ObjectId

CONN = "650000000000000000000001"
DB = "DBAAssistant"


def _auth(client):
    res = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


# ── Host-control (WinRM) endpoints ───────────────────────────────────────────

def test_get_host_control_hides_password(client):
    cfg = {"win_host": "h", "service_name": "MSSQLSERVER", "username": "u",
           "port": 5985, "transport": "ntlm", "has_password": True}
    with patch("app.services.connections_repo.get_host_control", return_value=cfg):
        res = client.get(f"/connections/{CONN}/host-control", headers=_auth(client))
    assert res.status_code == 200
    body = res.json()
    assert "password" not in body
    assert body["has_password"] is True and body["service_name"] == "MSSQLSERVER"


def test_get_host_control_404(client):
    with patch("app.services.connections_repo.get_host_control", return_value=None):
        res = client.get(f"/connections/{CONN}/host-control", headers=_auth(client))
    assert res.status_code == 404


def test_put_host_control_audits(client):
    saved = {"win_host": "", "service_name": "MSSQLSERVER", "username": "u",
             "port": 5985, "transport": "ntlm", "has_password": True}
    body = {"win_host": "", "service_name": "MSSQLSERVER", "username": "u",
            "password": "secret", "port": 5985, "transport": "ntlm"}
    with patch("app.services.connections_repo.set_host_control", return_value=True) as mock_set, \
         patch("app.services.connections_repo.get_host_control", return_value=saved), \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.put(f"/connections/{CONN}/host-control", json=body, headers=_auth(client))
    assert res.status_code == 200
    mock_set.assert_called_once()
    assert mock_audit.call_args.args[1] == "connection.host_control"


def test_put_host_control_connection_not_found(client):
    body = {"service_name": "MSSQLSERVER", "username": "u", "password": "p"}
    with patch("app.services.connections_repo.set_host_control", return_value=False):
        res = client.put(f"/connections/{CONN}/host-control", json=body, headers=_auth(client))
    assert res.status_code == 404


# ── Reglas CRUD ──────────────────────────────────────────────────────────────

RULE = {"id": "r1", "name": "Reiniciar SQL", "workaround_key": "start_sql_service",
        "connection_id": CONN, "database": "", "enabled": True, "min_rows": 1,
        "cooldown_seconds": 300, "last_triggered": None, "last_checked": None, "last_status": None}


def test_list_rules_requires_auth(client):
    assert client.get("/workarounds/rules").status_code == 401


def test_create_rule_ok(client):
    body = {"name": "Reiniciar SQL", "workaround_key": "start_sql_service", "connection_id": CONN}
    with patch("app.services.workarounds_repo.create_rule", return_value=RULE) as mock_create, \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.post("/workarounds/rules", json=body, headers=_auth(client))
    assert res.status_code == 201
    mock_create.assert_called_once()
    assert mock_audit.call_args.args[1] == "workaround.rule_create"


def test_create_rule_unknown_workaround_400(client):
    body = {"name": "x", "workaround_key": "ghost", "connection_id": CONN}
    with patch("app.services.workarounds_repo.get_custom", return_value=None):
        res = client.post("/workarounds/rules", json=body, headers=_auth(client))
    assert res.status_code == 400


def test_update_rule_ok(client):
    with patch("app.services.workarounds_repo.update_rule", return_value={**RULE, "enabled": False}), \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.put("/workarounds/rules/r1", json={"enabled": False}, headers=_auth(client))
    assert res.status_code == 200
    assert res.json()["enabled"] is False
    assert mock_audit.call_args.args[1] == "workaround.rule_update"


def test_update_rule_404(client):
    with patch("app.services.workarounds_repo.update_rule", return_value=None):
        res = client.put("/workarounds/rules/ghost", json={"enabled": False}, headers=_auth(client))
    assert res.status_code == 404


def test_delete_rule_ok(client):
    with patch("app.services.workarounds_repo.delete_rule", return_value=True), \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.delete("/workarounds/rules/r1", headers=_auth(client))
    assert res.status_code == 204
    assert mock_audit.call_args.args[1] == "workaround.rule_delete"


def test_delete_rule_404(client):
    with patch("app.services.workarounds_repo.delete_rule", return_value=False):
        res = client.delete("/workarounds/rules/ghost", headers=_auth(client))
    assert res.status_code == 404


def test_evaluate_endpoint_audits(client):
    fake = [{"rule_id": "r1", "name": "Reiniciar SQL", "workaround_key": "start_sql_service",
             "checked": True, "triggered": True, "problems": 1, "status": "Running"}]
    with patch("app.services.automation.evaluate_rules", return_value=fake) as mock_eval, \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.post("/workarounds/rules/evaluate", headers=_auth(client))
    assert res.status_code == 200
    assert res.json()[0]["triggered"] is True
    mock_eval.assert_called_once()
    assert mock_audit.call_args.args[1] == "workaround.evaluate"


# ── Motor de evaluación (automation.evaluate_rules) ──────────────────────────

def _raw_rule(**over):
    base = {"_id": ObjectId(), "name": "r1", "workaround_key": "k", "connection_id": CONN,
            "database": DB, "min_rows": 1, "cooldown_seconds": 300, "last_triggered": None}
    base.update(over)
    return base


def test_engine_triggers_when_problem_detected():
    from app.services import automation
    raw = _raw_rule()
    apply_mock = MagicMock(return_value="aplicado")
    with patch("app.services.workarounds_repo.list_enabled_rules_raw", return_value=[raw]), \
         patch("app.services.automation._resolve", return_value={"key": "k", "kind": "sql"}), \
         patch("app.services.automation._diagnose_count", return_value=(3, "3 filas")), \
         patch("app.services.automation._apply", apply_mock), \
         patch("app.services.workarounds_repo.log_run"), \
         patch("app.services.workarounds_repo.mark_checked") as mock_mark, \
         patch("app.services.audit_repo.log") as mock_audit:
        out = automation.evaluate_rules("tester")
    assert out[0]["triggered"] is True and out[0]["problems"] == 3
    apply_mock.assert_called_once()
    assert mock_audit.call_args.args[1] == "workaround.auto"
    assert mock_mark.call_args.kwargs.get("triggered") is True


def test_engine_no_trigger_below_threshold():
    from app.services import automation
    raw = _raw_rule(min_rows=5)
    apply_mock = MagicMock()
    with patch("app.services.workarounds_repo.list_enabled_rules_raw", return_value=[raw]), \
         patch("app.services.automation._resolve", return_value={"key": "k", "kind": "sql"}), \
         patch("app.services.automation._diagnose_count", return_value=(1, "1 fila")), \
         patch("app.services.automation._apply", apply_mock), \
         patch("app.services.workarounds_repo.mark_checked"), \
         patch("app.services.audit_repo.log"):
        out = automation.evaluate_rules("tester")
    assert out[0]["triggered"] is False and out[0]["checked"] is True
    apply_mock.assert_not_called()


def test_engine_respects_cooldown():
    from app.services import automation
    raw = _raw_rule(last_triggered=datetime.now(timezone.utc), cooldown_seconds=300)
    diag_mock = MagicMock()
    with patch("app.services.workarounds_repo.list_enabled_rules_raw", return_value=[raw]), \
         patch("app.services.automation._resolve", return_value={"key": "k", "kind": "sql"}), \
         patch("app.services.automation._diagnose_count", diag_mock), \
         patch("app.services.workarounds_repo.mark_checked"), \
         patch("app.services.audit_repo.log"):
        out = automation.evaluate_rules("tester")
    assert out[0]["checked"] is False and out[0]["triggered"] is False
    diag_mock.assert_not_called()


def test_engine_unknown_workaround_records_error():
    from app.services import automation
    raw = _raw_rule()
    with patch("app.services.workarounds_repo.list_enabled_rules_raw", return_value=[raw]), \
         patch("app.services.automation._resolve", return_value=None):
        out = automation.evaluate_rules("tester")
    assert out[0]["checked"] is False and out[0]["error"]
