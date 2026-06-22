# tests/unit/test_host_control.py
"""Tests del control de host WinRM por conexión (Sprint 10.1).

WinRM se mockea a nivel de funciones de host_control (nunca se importa winrm).
"""
from unittest.mock import patch

CONN = "650000000000000000000001"


def _auth(client):
    res = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


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
