# tests/unit/test_performance.py
"""Tests de performance POR CONEXIÓN (Sprint 4). Todo mockeado."""
from unittest.mock import patch

CONN = "650000000000000000000001"


def _token(client):
    res = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return res.json()["access_token"]


def test_metrics_requires_auth(client):
    assert client.get(f"/performance/{CONN}/metrics").status_code == 401


def test_metrics_connection_not_found(client):
    token = _token(client)
    with patch("app.services.connections_repo.get_engine", return_value=None):
        res = client.get(f"/performance/{CONN}/metrics", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_metrics_ok(client):
    token = _token(client)
    fake = {"cpu_percent": 12.0, "memory_percent": 60.0, "sessions": 3,
            "active_requests": 1, "connections": 5, "blocked": 0, "locks": 2}
    with patch("app.services.connections_repo.get_engine", return_value=object()), \
         patch("app.services.performance_repo.get_metrics", return_value=fake):
        res = client.get(f"/performance/{CONN}/metrics", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["sessions"] == 3


def test_sessions_ok(client):
    token = _token(client)
    fake = [{"session_id": 87, "login_name": "svc", "database_name": "Ventas",
             "status": "running", "command": "SELECT", "cpu_ms": 14820,
             "elapsed_ms": 134000, "blocking_session_id": None, "query_text": "SELECT ..."}]
    with patch("app.services.connections_repo.get_engine", return_value=object()), \
         patch("app.services.performance_repo.get_active_sessions", return_value=fake):
        res = client.get(f"/performance/{CONN}/sessions", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()[0]["session_id"] == 87


def test_top_queries_ok(client):
    token = _token(client)
    fake = [{"query_text": "SELECT 1", "execution_count": 124, "total_cpu_ms": 14820, "avg_cpu_ms": 119}]
    with patch("app.services.connections_repo.get_engine", return_value=object()), \
         patch("app.services.performance_repo.get_top_queries", return_value=fake):
        res = client.get(f"/performance/{CONN}/top-queries", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()[0]["total_cpu_ms"] == 14820
