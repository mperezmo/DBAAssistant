# tests/integration/test_live_services.py
"""Integration tests contra los servicios REALES (stack docker-compose levantado).

No corren en el CI por defecto (testpaths = tests/unit). Para ejecutarlos:
    docker-compose up -d
    python -m pytest tests/integration -v

Usan los puertos publicados al host: backend 8000, Mongo 27017, Redis 6379.
Cada test se SALTEA si su servicio no está disponible.
"""
from datetime import datetime, timezone

import httpx
import pytest

pytestmark = pytest.mark.integration

BACKEND = "http://localhost:8000"


def _get(path):
    try:
        return httpx.get(f"{BACKEND}{path}", timeout=4)
    except Exception:
        pytest.skip("backend no disponible en localhost:8000")


# ── API + stack completo ──
def test_health_live():
    res = _get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    # El backend (en su contenedor) realmente llega a las 3 bases:
    assert body["services"] == {"sqlserver": True, "mongo": True, "redis": True}


def test_root_live():
    res = _get("/")
    assert res.status_code == 200
    assert "message" in res.json()


def test_openapi_live():
    res = _get("/openapi.json")
    assert res.status_code == 200
    paths = res.json()["paths"]
    for expected in ["/health", "/auth/login", "/chat", "/cache/stats"]:
        assert expected in paths


def test_protected_route_requires_auth_live():
    res = _get("/auth/me")
    assert res.status_code == 401  # sin token


# ── MongoDB real ──
def test_mongo_live():
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
    except Exception:
        pytest.skip("MongoDB no disponible en localhost:27017")
    col = client["dba_assistant_itest"]["probe"]
    doc_id = col.insert_one({"ts": datetime.now(timezone.utc), "ok": True}).inserted_id
    assert col.find_one({"_id": doc_id})["ok"] is True
    col.delete_many({})


# ── Redis real ──
def test_redis_live():
    try:
        import redis
        r = redis.from_url("redis://localhost:6379/0", socket_connect_timeout=2)
        r.ping()
    except Exception:
        pytest.skip("Redis no disponible en localhost:6379")
    r.set("itest:probe", "1", ex=30)
    assert r.get("itest:probe") == b"1"
    r.delete("itest:probe")
