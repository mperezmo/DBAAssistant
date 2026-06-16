# tests/unit/test_audit.py
"""Tests de auditoría (Sprint 4)."""
from unittest.mock import patch


def _token(client):
    res = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return res.json()["access_token"]


def test_audit_requires_auth(client):
    assert client.get("/audit").status_code == 401


def test_audit_list(client):
    token = _token(client)
    fake = [{"id": "1", "timestamp": "2026-06-14T10:00:00+00:00", "user": "admin@dba.local",
             "action": "connection.create", "target": "LocalHost", "detail": "h:1433", "ip": "172.18.0.1"}]
    with patch("app.services.audit_repo.list_recent", return_value=fake):
        res = client.get("/audit", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()[0]["action"] == "connection.create"


def test_create_connection_writes_audit(client):
    token = _token(client)
    public = {"id": "abc", "name": "LocalHost", "host": "h", "port": 1433, "username": "sa"}
    body = {"name": "LocalHost", "host": "h", "port": 1433, "username": "sa", "password": "x"}
    with patch("app.services.connections_repo.create", return_value=public), \
         patch("app.services.audit_repo.log") as mock_log:
        res = client.post("/connections", json=body, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201
    mock_log.assert_called_once()
    assert mock_log.call_args.args[1] == "connection.create"
