# tests/unit/test_schema.py
"""Tests de metadata/esquema POR CONEXIÓN (Sprint 4). Todo mockeado."""
from unittest.mock import patch

CONN = "650000000000000000000001"


def _token(client):
    res = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return res.json()["access_token"]


def test_overview_requires_auth(client):
    assert client.get(f"/schema/{CONN}/overview").status_code == 401


def test_overview_connection_not_found(client):
    token = _token(client)
    with patch("app.services.connections_repo.get_engine", return_value=None):
        res = client.get(f"/schema/{CONN}/overview", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_overview_ok(client):
    token = _token(client)
    fake = {"server": "PC\\SQLEXPRESS", "database": "Ventas", "table_count": 4, "total_size_kb": 576}
    with patch("app.services.connections_repo.get_engine", return_value=object()), \
         patch("app.services.schema_repo.get_overview", return_value=fake):
        res = client.get(f"/schema/{CONN}/overview", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["database"] == "Ventas"
    assert res.json()["server"] == "PC\\SQLEXPRESS"


def test_tables_ok(client):
    token = _token(client)
    fake = [{"schema_name": "dbo", "table_name": "clientes", "row_count": 3,
             "size_kb": 144, "column_count": 5, "index_count": 2}]
    with patch("app.services.connections_repo.get_engine", return_value=object()), \
         patch("app.services.schema_repo.list_tables", return_value=fake):
        res = client.get(f"/schema/{CONN}/tables", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()[0]["table_name"] == "clientes"


def test_table_detail_404(client):
    token = _token(client)
    with patch("app.services.connections_repo.get_engine", return_value=object()), \
         patch("app.services.schema_repo.get_table_detail", return_value=None):
        res = client.get(f"/schema/{CONN}/tables/dbo/nope", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404
