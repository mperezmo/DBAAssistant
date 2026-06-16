# backend/app/services/connections_repo.py
"""Gestor de conexiones a INSTANCIAS de SQL Server (Sprint 4).

Las conexiones se guardan en MongoDB (colección `connections`). Cada conexión
es a una instancia; se conecta a `master` para listar bases y leer DMVs de
servidor. Para analizar el esquema de una base puntual se construye un engine
por (conexión, base).

⚠️ SEGURIDAD: la contraseña se guarda tal cual en Mongo (dev/TFI). En producción
debería cifrarse o usar Azure Key Vault. La contraseña NUNCA se devuelve.
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

# Bases no analizables: sistema (database_id <= 4) y ReportServer.
_DATABASES_SQL = """
SELECT name FROM sys.databases
WHERE database_id > 4
  AND name NOT IN ('ReportServer', 'ReportServerTempDB')
  AND state_desc = 'ONLINE'
ORDER BY name
"""


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
    }


def _build_url(cfg: dict, database: str = "master") -> str:
    return Settings._odbc_url(cfg["username"], cfg["password"], cfg["host"], cfg["port"], database)


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
    for key in [k for k in list(_engines) if k == connection_id or k.startswith(f"{connection_id}::")]:
        _engines.pop(key).dispose()
    return _col.delete_one({"_id": oid}).deleted_count > 0


def get_engine(connection_id: str) -> Engine | None:
    """Engine a la instancia (base `master`). Para listar bases y DMVs."""
    if connection_id in _engines:
        return _engines[connection_id]
    oid = _oid(connection_id)
    if not oid:
        return None
    raw = _col.find_one({"_id": oid})
    if not raw:
        return None
    eng = create_engine(_build_url(raw, "master"), pool_pre_ping=True)
    _engines[connection_id] = eng
    return eng


def list_databases(connection_id: str) -> list[str] | None:
    """Bases de datos analizables de la instancia (None si la conexión no existe)."""
    eng = get_engine(connection_id)
    if eng is None:
        return None
    with eng.connect() as conn:
        return [row[0] for row in conn.execute(text(_DATABASES_SQL))]


def get_engine_for_db(connection_id: str, database: str) -> Engine | None:
    """Engine a una base puntual de la instancia. None si conexión o base inválida."""
    oid = _oid(connection_id)
    if not oid:
        return None
    key = f"{connection_id}::{database}"
    if key in _engines:
        return _engines[key]
    raw = _col.find_one({"_id": oid})
    if not raw:
        return None
    allowed = list_databases(connection_id)  # valida que la base exista y sea permitida
    if not allowed or database not in allowed:
        return None
    eng = create_engine(_build_url(raw, database), pool_pre_ping=True)
    _engines[key] = eng
    return eng


def test(data: dict) -> tuple[bool, str | None, str | None]:
    """Prueba la conexión a la instancia (sin guardarla). Devuelve (ok, error, server)."""
    try:
        eng = create_engine(_build_url(data, "master"), connect_args={"timeout": 5})
        try:
            with eng.connect() as conn:
                server = conn.execute(text("SELECT @@SERVERNAME")).scalar()
            return True, None, str(server)
        finally:
            eng.dispose()
    except Exception as exc:  # noqa: BLE001
        return False, str(exc), None
