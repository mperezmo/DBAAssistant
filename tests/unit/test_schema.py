# tests/unit/test_schema.py
"""Tests de metadata/esquema (Sprint 4). schema_repo mockeado (sin SQL Server real)."""
from unittest.mock import patch


def _token(client):
    res = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return res.json()["access_token"]


def test_overview_requires_auth(client):
    assert client.get("/schema/overview").status_code == 401


def test_tables_requires_auth(client):
    assert client.get("/schema/tables").status_code == 401


def test_overview_with_token(client):
    token = _token(client)
    fake = {"database": "DBAAssistant", "table_count": 4, "total_size_kb": 576}
    with patch("app.services.schema_repo.get_overview", return_value=fake):
        res = client.get("/schema/overview", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["table_count"] == 4


def test_tables_with_token(client):
    token = _token(client)
    fake = [{"schema_name": "dbo", "table_name": "clientes", "row_count": 3,
             "size_kb": 144, "column_count": 5, "index_count": 2}]
    with patch("app.services.schema_repo.list_tables", return_value=fake):
        res = client.get("/schema/tables", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()[0]["table_name"] == "clientes"


def test_table_detail_404(client):
    token = _token(client)
    with patch("app.services.schema_repo.get_table_detail", return_value=None):
        res = client.get("/schema/tables/dbo/nope", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_table_detail_ok(client):
    token = _token(client)
    fake = {
        "schema_name": "dbo", "table_name": "clientes",
        "columns": [{"name": "id", "data_type": "int", "max_length": 4,
                     "is_nullable": False, "is_primary_key": True}],
        "indexes": [{"name": "PK_clientes", "type_desc": "CLUSTERED",
                     "is_unique": True, "is_primary_key": True}],
        "foreign_keys": [],
    }
    with patch("app.services.schema_repo.get_table_detail", return_value=fake):
        res = client.get("/schema/tables/dbo/clientes", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["columns"][0]["is_primary_key"] is True
