# backend/app/services/db.py
from sqlalchemy import create_engine, text
from pymongo import MongoClient
import redis

from app.config import get_settings

settings = get_settings()

# Engines/clients se crean una vez (lazy en producción real, simple aquí)
sql_engine = create_engine(settings.sqlserver_url, pool_pre_ping=True)
# Motor "target": SQL Server a analizar (tu instancia local). Si no hay target
# configurado, apunta a la misma conexión principal.
target_engine = create_engine(settings.target_sqlserver_url, pool_pre_ping=True)
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