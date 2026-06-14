# tests/unit/test_health.py
from unittest.mock import patch


def test_root(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["message"] == "DBA Assistant API running"


def test_health_all_ok(client):
    with patch("app.services.db.check_sqlserver", return_value=True), \
         patch("app.services.db.check_mongo", return_value=True), \
         patch("app.services.db.check_redis", return_value=True):
        res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["services"] == {"sqlserver": True, "mongo": True, "redis": True}


def test_health_degraded_when_a_service_down(client):
    with patch("app.services.db.check_sqlserver", return_value=True), \
         patch("app.services.db.check_mongo", return_value=False), \
         patch("app.services.db.check_redis", return_value=True):
        res = client.get("/health")
    assert res.json()["status"] == "degraded"