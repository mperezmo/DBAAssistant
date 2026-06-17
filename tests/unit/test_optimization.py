# tests/unit/test_optimization.py
"""Tests de optimización de índices (Sprint 6). Mockeado."""
from unittest.mock import patch

CONN = "650000000000000000000001"
DB = "DBAAssistant"


def _token(client):
    res = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return res.json()["access_token"]


def test_missing_requires_auth(client):
    assert client.get(f"/optimization/{CONN}/{DB}/missing-indexes").status_code == 401


def test_missing_connection_not_found(client):
    token = _token(client)
    with patch("app.services.connections_repo.get_engine_for_db", return_value=None):
        res = client.get(f"/optimization/{CONN}/{DB}/missing-indexes", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_missing_ok(client):
    token = _token(client)
    fake = [{"schema_name": "dbo", "table_name": "clientes", "impact": 1200.0,
             "avg_impact_pct": 95.0, "uses": 3, "equality_columns": "[ciudad]",
             "inequality_columns": None, "included_columns": None,
             "create_statement": "CREATE NONCLUSTERED INDEX [IX_clientes_ciudad] ON [dbo].[clientes] ([ciudad]);"}]
    with patch("app.services.connections_repo.get_engine_for_db", return_value=object()), \
         patch("app.services.optimization_repo.missing_indexes", return_value=fake):
        res = client.get(f"/optimization/{CONN}/{DB}/missing-indexes", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()[0]["create_statement"].startswith("CREATE NONCLUSTERED INDEX")


def test_unused_ok(client):
    token = _token(client)
    fake = [{"schema_name": "dbo", "table_name": "clientes", "index_name": "IX_clientes_email",
             "type_desc": "NONCLUSTERED", "user_seeks": 0, "user_scans": 0, "user_lookups": 0,
             "user_updates": 5, "drop_statement": "DROP INDEX [IX_clientes_email] ON [dbo].[clientes];"}]
    with patch("app.services.connections_repo.get_engine_for_db", return_value=object()), \
         patch("app.services.optimization_repo.unused_indexes", return_value=fake):
        res = client.get(f"/optimization/{CONN}/{DB}/unused-indexes", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()[0]["drop_statement"].startswith("DROP INDEX")
