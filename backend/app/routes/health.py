# backend/app/routes/health.py
from fastapi import APIRouter

from app.services import db

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    checks = {
        "sqlserver": db.check_sqlserver(),
        "mongo": db.check_mongo(),
        "redis": db.check_redis(),
    }
    status = "ok" if all(checks.values()) else "degraded"
    return {"status": status, "services": checks}