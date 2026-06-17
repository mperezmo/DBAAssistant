# backend/app/services/cache.py
"""Capa de caché en Redis para metadata (Sprint 6).

Cachea resultados semi-estáticos (bases, esquema) con TTL e invalidación por
conexión. Todo es tolerante a fallos: si Redis no responde, se comporta como un
cache miss (la app sigue funcionando sin caché).

Convención de claves: cache:data:{tipo}:{connection_id}:{...}
"""
import json
import time

from app.services.db import redis_client

DEFAULT_TTL = 300  # 5 minutos
_HITS = "cache:stats:hits"
_MISSES = "cache:stats:misses"

# Circuit breaker: si Redis falla, no se reintenta durante este lapso. Evita
# pagar el timeout de conexión en cada request cuando Redis está caído.
_COOLDOWN = 10
_down_until = 0.0


def _down() -> bool:
    return time.time() < _down_until


def _mark_down() -> None:
    global _down_until
    _down_until = time.time() + _COOLDOWN


def get_json(key: str):
    if _down():
        return None
    try:
        value = redis_client.get(key)
    except Exception:
        _mark_down()
        return None
    try:
        if value is not None:
            redis_client.incr(_HITS)
            return json.loads(value)
        redis_client.incr(_MISSES)
    except Exception:
        _mark_down()
    return None


def set_json(key: str, value, ttl: int = DEFAULT_TTL) -> None:
    if _down():
        return
    try:
        redis_client.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception:
        _mark_down()


def _delete_match(pattern: str) -> int:
    if _down():
        return 0
    try:
        keys = list(redis_client.scan_iter(match=pattern))
        if keys:
            redis_client.delete(*keys)
        return len(keys)
    except Exception:
        _mark_down()
        return 0


def invalidate_connection(connection_id: str) -> int:
    """Borra todas las entradas de caché de una conexión."""
    return _delete_match(f"cache:data:*{connection_id}*")


def clear() -> int:
    n = _delete_match("cache:data:*")
    try:
        redis_client.delete(_HITS, _MISSES)
    except Exception:
        pass
    return n


def stats() -> dict:
    if _down():
        return {"hits": None, "misses": None, "keys": None, "hit_ratio": None}
    try:
        hits = int(redis_client.get(_HITS) or 0)
        misses = int(redis_client.get(_MISSES) or 0)
        keys = sum(1 for _ in redis_client.scan_iter(match="cache:data:*"))
        total = hits + misses
        ratio = round(hits / total * 100, 1) if total else None
        return {"hits": hits, "misses": misses, "keys": keys, "hit_ratio": ratio}
    except Exception:
        _mark_down()
        return {"hits": None, "misses": None, "keys": None, "hit_ratio": None}
