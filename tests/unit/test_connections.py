# tests/unit/test_connections.py
"""Tests del gestor de conexiones a instancias (Sprint 4). connections_repo mockeado."""
from unittest.mock import patch

CONN = "650000000000000000000001"
_BODY = {"name": "LocalHost", "host": "host.docker.internal", "port": 1433,
         "username": "sa", "password": "secreto"}


def _token(client):
    res = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return res.json()["access_token"]


def test_list_requires_auth(client):
    assert client.get("/connections").status_code == 401


def test_create_does_not_leak_password(client):
    token = _token(client)
    public = {"id": "abc123", "name": "LocalHost", "host": "host.docker.internal",
              "port": 1433, "username": "sa"}
    with patch("app.services.connections_repo.create", return_value=public):
        res = client.post("/connections", json=_BODY, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201
    body = res.json()
    assert body["id"] == "abc123"
    assert "password" not in body
    assert "database" not in body  # la conexión es a la instancia, no a una base


def test_list_databases(client):
    token = _token(client)
    with patch("app.services.connections_repo.list_databases", return_value=["DBAAssistant", "MXApp"]):
        res = client.get(f"/connections/{CONN}/databases", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json() == ["DBAAssistant", "MXApp"]


def test_list_databases_connection_not_found(client):
    token = _token(client)
    with patch("app.services.connections_repo.list_databases", return_value=None):
        res = client.get(f"/connections/{CONN}/databases", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_test_connection_ok(client):
    token = _token(client)
    with patch("app.services.connections_repo.test", return_value=(True, None, "PC\\SQLEXPRESS")):
        res = client.post("/connections/test", json=_BODY, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["server"] == "PC\\SQLEXPRESS"


def test_delete_not_found(client):
    token = _token(client)
    with patch("app.services.connections_repo.delete", return_value=False):
        res = client.delete("/connections/xxx", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404
