# tests/unit/test_units.py
"""Unit tests de utilidades/servicios (sin red): config, cache, keyvault, etc."""
from datetime import datetime
from unittest.mock import MagicMock

from app import keyvault
from app.config import Settings, get_settings
from app.services import cache, claude, sql_executor, sql_validator


# ── config ──
def test_odbc_url_encodes_special_chars():
    url = Settings._odbc_url("user", "p@ss:w/d", "host", 1433, "My DB")
    assert "p%40ss%3Aw%2Fd" in url       # @ : / codificados
    assert "My%20DB" in url               # espacio codificado
    assert "host:1433" in url


def test_cors_list():
    s = get_settings()
    assert isinstance(s.cors_list, list)
    assert all(isinstance(o, str) for o in s.cors_list)


# ── keyvault (no-op sin AZURE_VAULT_URL) ──
def test_keyvault_noop(monkeypatch):
    monkeypatch.delenv("AZURE_VAULT_URL", raising=False)
    assert keyvault.load_secrets() is None  # no rompe, no hace nada


# ── claude: limpieza de fences ──
def test_strip_fences():
    assert claude._strip_fences("```sql\nSELECT 1\n```") == "SELECT 1"
    assert claude._strip_fences("```\nSELECT 2\n```") == "SELECT 2"
    assert claude._strip_fences("SELECT 3") == "SELECT 3"


# ── sql_validator ──
def test_validator_warnings():
    assert sql_validator.analyze("DROP TABLE x") != []
    assert sql_validator.analyze("UPDATE x SET a=1") != []
    assert sql_validator.analyze("UPDATE x SET a=1 WHERE id=2") == []


def test_sql_executor_safe():
    assert sql_executor._safe(5) == 5
    assert sql_executor._safe(None) is None
    assert sql_executor._safe("a") == "a"
    assert isinstance(sql_executor._safe(datetime.now()), str)  # no JSON-nativo → str


# ── cache: circuit breaker (sin Redis real) ──
def test_cache_circuit_breaker(monkeypatch):
    cache._down_until = 0.0
    bad = MagicMock()
    bad.get.side_effect = Exception("redis down")
    monkeypatch.setattr(cache, "redis_client", bad)

    assert cache.get_json("k") is None      # falla → None y marca "down"
    assert cache._down() is True

    cache.set_json("k", {"a": 1})           # estando down, no toca Redis
    bad.set.assert_not_called()

    cache._down_until = 0.0                  # reset para no afectar otros tests
