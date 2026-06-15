# backend/app/services/db.py
from sqlalchemy import create_engine, text
from pymongo import MongoClient
import redis

from app.config import get_settings

settings = get_settings()

# Engines/clients se crean una vez (lazy en producción real, simple aquí).
# Nota: las conexiones a analizar (target) ahora son dinámicas y las gestiona
# connections_repo (creadas desde el Panel Admin), no esta conexión fija.
sql_engine = create_engine(settings.sqlserver_url, pool_pre_ping=True)
mongo_client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=2000)
redis_client = redis.from_url(settings.redis_url, socket_connect_timeout=2)


def check_sqlserver() -> bool:
    try:
        with sql_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def check_mongo() -> bool:
    try:
        mongo_client.admin.command("ping")
        return True
    except Exception:
        return False


def check_redis() -> bool:
    try:
        return bool(redis_client.ping())
    except Exception:
        return False