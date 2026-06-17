# tests/unit/test_cache.py
"""Tests de la caché Redis (Sprint 6)."""
from unittest.mock import patch

from app.services import cache


def _token(client):
    res = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    return res.json()["access_token"]


def test_get_json_graceful_without_redis():
    # En el host no hay Redis alcanzable → get_json degrada a None (cache miss).
    assert cache.get_json("cache:data:noexiste") is None


def test_stats_requires_auth(client):
    assert client.get("/cache/stats").status_code == 401


def test_stats_ok(client):
    token = _token(client)
    fake = {"hits": 10, "misses": 4, "keys": 6, "hit_ratio": 71.4}
    with patch("app.services.cache.stats", return_value=fake):
        res = client.get("/cache/stats", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["hit_ratio"] == 71.4


def test_clear_ok(client):
    token = _token(client)
    with patch("app.services.cache.clear", return_value=7):
        res = client.post("/cache/clear", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["cleared_keys"] == 7
