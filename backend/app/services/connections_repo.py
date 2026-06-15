# backend/app/services/connections_repo.py
"""Gestor de conexiones a SQL Server (Sprint 4).

Las conexiones se guardan en MongoDB (colección `connections`). Cada conexión
genera (y cachea) un engine de SQLAlchemy para analizar esa instancia.

⚠️ SEGURIDAD: la contraseña se guarda tal cual en Mongo (suficiente para
dev/TFI). En producción debería cifrarse o usar Azure Key Vault. La contraseña
NUNCA se devuelve por la API.
"""
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import Settings, get_settings
from app.services.db import mongo_client

settings = get_settings()
_col = mongo_client[settings.mongodb_database]["connections"]
_engines: dict[str, Engine] = {}


def _oid(connection_id: str) -> ObjectId | None:
    try:
        return ObjectId(connection_id)
    except (InvalidId, TypeError):
        return None


def _public(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "host": doc["host"],
        "port": doc["port"],
        "username": doc["username"],
        "database": doc["database"],
    }


def _build_url(cfg: dict) -> str:
    return Settings._odbc_url(
        cfg["username"], cfg["password"], cfg["host"], cfg["port"], cfg["database"]
    )


def create(data: dict) -> dict:
    doc = {**data, "created_at": datetime.now(timezone.utc)}
    res = _col.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _public(doc)


def list_all() -> list[dict]:
    return [_public(d) for d in _col.find().sort("created_at", 1)]


def delete(connection_id: str) -> bool:
    oid = _oid(connection_id)
    if not oid:
        return False
    eng = _engines.pop(connection_id, None)
    if eng is not None:
        eng.dispose()
    return _col.delete_one({"_id": oid}).deleted_count > 0


def get_engine(connection_id: str) -> Engine | None:
    """Devuelve (cacheado) el engine de la conexión, o None si no existe."""
    if connection_id in _engines:
        return _engines[connection_id]
    oid = _oid(connection_id)
    if not oid:
        return None
    raw = _col.find_one({"_id": oid})
    if not raw:
        return None
    eng = create_engine(_build_url(raw), pool_pre_ping=True)
    _engines[connection_id] = eng
    return eng


def test(data: dict) -> tuple[bool, str | None, str | None]:
    """Prueba una conexión sin guardarla. Devuelve (ok, error, server_name)."""
    try:
        eng = create_engine(_build_url(data), connect_args={"timeout": 5})
        try:
            with eng.connect() as conn:
                server = conn.execute(text("SELECT @@SERVERNAME")).scalar()
            return True, None, str(server)
        finally:
            eng.dispose()
    except Exception as exc:  # noqa: BLE001
        return False, str(exc), None
