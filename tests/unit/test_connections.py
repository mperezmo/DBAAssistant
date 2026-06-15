# tests/unit/test_connections.py
"""Tests del gestor de conexiones (Sprint 4). connections_repo mockeado."""
from unittest.mock import patch

_BODY = {"name": "Local", "host": "host.docker.internal", "port": 14333,
         "username": "sa", "password": "secreto", "database": "Ventas"}


def _token(client):
    res = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return res.json()["access_token"]


def test_list_requires_auth(client):
    assert client.get("/connections").status_code == 401


def test_create_does_not_leak_password(client):
    token = _token(client)
    public = {"id": "abc123", "name": "Local", "host": "host.docker.internal",
              "port": 14333, "username": "sa", "database": "Ventas"}
    with patch("app.services.connections_repo.create", return_value=public):
        res = client.post("/connections", json=_BODY, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201
    body = res.json()
    assert body["id"] == "abc123"
    assert "password" not in body


def test_list_connections(client):
    token = _token(client)
    with patch("app.services.connections_repo.list_all", return_value=[]):
        res = client.get("/connections", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json() == []


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
