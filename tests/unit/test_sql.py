# tests/unit/test_sql.py
"""Tests de generación y ejecución de SQL (Sprint 5). Mockeado."""
from unittest.mock import patch

from app.services import sql_validator

CONN = "650000000000000000000001"
DB = "DBAAssistant"


def _token(client):
    res = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return res.json()["access_token"]


# ── validador (unit puro) ──
def test_validator_delete_without_where():
    assert sql_validator.analyze("DELETE FROM t") != []
    assert sql_validator.analyze("DELETE FROM t WHERE id=1") == []


def test_validator_is_read_only():
    assert sql_validator.is_read_only("SELECT 1")
    assert sql_validator.is_read_only("  with x as (select 1) select * from x")
    assert not sql_validator.is_read_only("UPDATE t SET a=1")


# ── endpoints ──
def test_execute_requires_auth(client):
    assert client.post("/sql/execute", json={"connection_id": CONN, "database": DB, "sql": "SELECT 1"}).status_code == 401


def test_generate_without_api_key(client):
    token = _token(client)
    with patch("app.services.claude.is_configured", return_value=False):
        res = client.post("/sql/generate", json={"prompt": "dame los clientes"}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 503


def test_execute_select(client):
    token = _token(client)
    fake = {"kind": "select", "columns": ["id", "nombre"], "rows": [[1, "Marina"]],
            "affected_rows": None, "committed": False, "elapsed_ms": 5}
    with patch("app.services.connections_repo.get_engine_for_db", return_value=object()), \
         patch("app.services.sql_executor.run", return_value=fake), \
         patch("app.services.query_history_repo.add"), \
         patch("app.services.audit_repo.log"):
        res = client.post("/sql/execute", json={"connection_id": CONN, "database": DB, "sql": "SELECT id, nombre FROM clientes"},
                          headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["kind"] == "select"
    assert body["columns"] == ["id", "nombre"]


def test_execute_write_preview_warns(client):
    token = _token(client)
    fake = {"kind": "write", "columns": None, "rows": None, "affected_rows": 3,
            "committed": False, "elapsed_ms": 8}
    with patch("app.services.connections_repo.get_engine_for_db", return_value=object()), \
         patch("app.services.sql_executor.run", return_value=fake), \
         patch("app.services.query_history_repo.add"), \
         patch("app.services.audit_repo.log"):
        res = client.post("/sql/execute", json={"connection_id": CONN, "database": DB, "sql": "DELETE FROM clientes", "mode": "preview"},
                          headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["committed"] is False
    assert any("DELETE sin WHERE" in w for w in body["warnings"])


def test_execute_connection_not_found(client):
    token = _token(client)
    with patch("app.services.connections_repo.get_engine_for_db", return_value=None):
        res = client.post("/sql/execute", json={"connection_id": CONN, "database": DB, "sql": "SELECT 1"},
                          headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_export_requires_auth(client):
    assert client.post("/sql/export", json={"connection_id": CONN, "database": DB, "sql": "SELECT 1"}).status_code == 401


def test_export_rejects_write(client):
    token = _token(client)
    res = client.post("/sql/export", json={"connection_id": CONN, "database": DB, "sql": "DELETE FROM t"},
                      headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400


def test_export_csv(client):
    token = _token(client)
    with patch("app.services.connections_repo.get_engine_for_db", return_value=object()), \
         patch("app.services.sql_executor.run_select", return_value=(["id", "nombre"], [[1, "Marina"], [2, "Tomás"]], False)), \
         patch("app.services.audit_repo.log"):
        res = client.post("/sql/export", json={"connection_id": CONN, "database": DB, "sql": "SELECT * FROM clientes"},
                          headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "id,nombre" in res.text and "Marina" in res.text
