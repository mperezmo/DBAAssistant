# tests/unit/test_workarounds.py
"""Tests de la biblioteca de Workarounds (Sprint 10). Repos/executor mockeados."""
from unittest.mock import patch

CONN = "650000000000000000000001"
DB = "DBAAssistant"


def _token(client):
    res = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return res.json()["access_token"]


def _auth(client):
    return {"Authorization": f"Bearer {_token(client)}"}


def test_list_requires_auth(client):
    assert client.get("/workarounds").status_code == 401


def test_list_returns_builtins(client):
    with patch("app.services.workarounds_repo.list_custom", return_value=[]), \
         patch("app.services.workarounds_repo.run_stats", return_value={}):
        res = client.get("/workarounds", headers=_auth(client))
    assert res.status_code == 200
    keys = {w["key"] for w in res.json()}
    assert "kill_blocking_sessions" in keys
    assert "force_checkpoint" in keys
    assert len(res.json()) >= 6


def test_list_merges_run_stats(client):
    stats = {"force_checkpoint": {"runs": 3, "last_run": "2026-06-22T10:00:00+00:00"}}
    with patch("app.services.workarounds_repo.list_custom", return_value=[]), \
         patch("app.services.workarounds_repo.run_stats", return_value=stats):
        res = client.get("/workarounds", headers=_auth(client))
    cp = next(w for w in res.json() if w["key"] == "force_checkpoint")
    assert cp["runs"] == 3 and cp["last_run"].startswith("2026-06-22")


def test_run_unknown_key_404(client):
    with patch("app.services.workarounds_repo.get_custom", return_value=None):
        res = client.post("/workarounds/nope/run",
                          json={"connection_id": CONN, "database": DB, "mode": "diagnose"},
                          headers=_auth(client))
    assert res.status_code == 404


def test_run_diagnose_connection_not_found(client):
    with patch("app.services.connections_repo.get_engine_for_db", return_value=None):
        res = client.post("/workarounds/force_checkpoint/run",
                          json={"connection_id": CONN, "database": DB, "mode": "diagnose"},
                          headers=_auth(client))
    assert res.status_code == 404


def test_run_diagnose_ok_audits(client):
    cols, rows = ["database_name", "recovery_model_desc"], [["DBAAssistant", "SIMPLE"]]
    with patch("app.services.connections_repo.get_engine_for_db", return_value=object()), \
         patch("app.services.sql_executor.run_select", return_value=(cols, rows, False)), \
         patch("app.services.workarounds_repo.log_run") as mock_log, \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.post("/workarounds/force_checkpoint/run",
                          json={"connection_id": CONN, "database": DB, "mode": "diagnose"},
                          headers=_auth(client))
    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "diagnose" and body["columns"] == cols and body["rows"] == rows
    mock_log.assert_called_once()
    assert mock_audit.call_args.args[1] == "workaround.run"


def test_run_apply_ok_invalidates_cache_and_audits(client):
    with patch("app.services.connections_repo.get_engine_for_db", return_value=object()), \
         patch("app.services.sql_executor.run_script", return_value={"affected_rows": 5, "elapsed_ms": 12}), \
         patch("app.services.cache.invalidate_connection") as mock_inv, \
         patch("app.services.workarounds_repo.log_run"), \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.post("/workarounds/update_stale_statistics/run",
                          json={"connection_id": CONN, "database": DB, "mode": "apply"},
                          headers=_auth(client))
    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "apply" and body["affected_rows"] == 5
    mock_inv.assert_called_once_with(CONN)
    assert mock_audit.call_args.args[1] == "workaround.run"


def test_run_apply_error_logs_failure(client):
    with patch("app.services.connections_repo.get_engine_for_db", return_value=object()), \
         patch("app.services.sql_executor.run_script", side_effect=Exception("boom")), \
         patch("app.services.workarounds_repo.log_run") as mock_log, \
         patch("app.services.audit_repo.log"):
        res = client.post("/workarounds/force_checkpoint/run",
                          json={"connection_id": CONN, "database": DB, "mode": "apply"},
                          headers=_auth(client))
    assert res.status_code == 400
    assert mock_log.call_args.kwargs.get("success") is False


def test_create_custom_ok_audits(client):
    body = {"key": "reindex_x", "name": "Reindex X", "description": "d",
            "category": "Performance", "severity": "warning",
            "diagnose_sql": "SELECT 1", "apply_sql": "ALTER INDEX ALL ON dbo.x REBUILD;"}
    created = {**body, "builtin": False, "requires_server_state": False}
    with patch("app.services.workarounds_repo.create_custom", return_value=created) as mock_create, \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.post("/workarounds", json=body, headers=_auth(client))
    assert res.status_code == 201
    assert res.json()["key"] == "reindex_x"
    mock_create.assert_called_once()
    assert mock_audit.call_args.args[1] == "workaround.create"


def test_create_rejects_non_select_diagnose(client):
    body = {"key": "bad", "name": "Bad", "diagnose_sql": "DELETE FROM x", "apply_sql": "DELETE FROM x"}
    res = client.post("/workarounds", json=body, headers=_auth(client))
    assert res.status_code == 400


def test_create_rejects_builtin_key(client):
    body = {"key": "force_checkpoint", "name": "dup", "diagnose_sql": "SELECT 1", "apply_sql": "CHECKPOINT;"}
    res = client.post("/workarounds", json=body, headers=_auth(client))
    assert res.status_code == 409


def test_delete_builtin_rejected(client):
    res = client.delete("/workarounds/force_checkpoint", headers=_auth(client))
    assert res.status_code == 400


def test_delete_custom_ok_audits(client):
    with patch("app.services.workarounds.get_builtin", return_value=None), \
         patch("app.services.workarounds_repo.delete_custom", return_value=True), \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.delete("/workarounds/reindex_x", headers=_auth(client))
    assert res.status_code == 204
    assert mock_audit.call_args.args[1] == "workaround.delete"


def test_delete_custom_not_found(client):
    with patch("app.services.workarounds.get_builtin", return_value=None), \
         patch("app.services.workarounds_repo.delete_custom", return_value=False):
        res = client.delete("/workarounds/ghost", headers=_auth(client))
    assert res.status_code == 404


# ── Workaround de servicio (kind=service, WinRM) · Sprint 10.1 ────────────────

_HC = {"host": "host.docker.internal", "port": 5985, "transport": "ntlm",
       "username": "u", "password": "p", "service_name": "MSSQLSERVER"}


def test_service_diagnose_stopped_returns_problem_row(client):
    with patch("app.services.connections_repo.host_control_config", return_value=_HC), \
         patch("app.services.host_control.service_status",
               return_value={"service_name": "MSSQLSERVER", "status": "Stopped"}), \
         patch("app.services.workarounds_repo.log_run"), \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.post("/workarounds/start_sql_service/run",
                          json={"connection_id": CONN, "mode": "diagnose"}, headers=_auth(client))
    assert res.status_code == 200
    body = res.json()
    assert body["rows"] == [["MSSQLSERVER", "Stopped"]]
    assert "Stopped" in body["message"]
    assert mock_audit.call_args.args[1] == "workaround.run"


def test_service_diagnose_running_no_rows(client):
    with patch("app.services.connections_repo.host_control_config", return_value=_HC), \
         patch("app.services.host_control.service_status",
               return_value={"service_name": "MSSQLSERVER", "status": "Running"}), \
         patch("app.services.workarounds_repo.log_run"), \
         patch("app.services.audit_repo.log"):
        res = client.post("/workarounds/start_sql_service/run",
                          json={"connection_id": CONN, "mode": "diagnose"}, headers=_auth(client))
    assert res.status_code == 200
    assert res.json()["rows"] == []


def test_service_apply_starts_service(client):
    with patch("app.services.connections_repo.host_control_config", return_value=_HC), \
         patch("app.services.host_control.start_service",
               return_value={"service_name": "MSSQLSERVER", "status": "Running"}), \
         patch("app.services.workarounds_repo.log_run"), \
         patch("app.services.audit_repo.log") as mock_audit:
        res = client.post("/workarounds/start_sql_service/run",
                          json={"connection_id": CONN, "mode": "apply"}, headers=_auth(client))
    assert res.status_code == 200
    assert "Running" in res.json()["message"]
    assert mock_audit.call_args.args[1] == "workaround.run"


def test_service_without_host_control_400(client):
    with patch("app.services.connections_repo.host_control_config", return_value=None), \
         patch("app.services.workarounds_repo.log_run"), \
         patch("app.services.audit_repo.log"):
        res = client.post("/workarounds/start_sql_service/run",
                          json={"connection_id": CONN, "mode": "diagnose"}, headers=_auth(client))
    assert res.status_code == 400
