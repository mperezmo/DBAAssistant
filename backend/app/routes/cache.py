# backend/app/routes/cache.py
"""Estadísticas y gestión de la caché Redis (Sprint 6). Protegido por auth."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.models.auth import User
from app.services import cache

router = APIRouter(prefix="/cache", tags=["cache"])


class CacheStats(BaseModel):
    hits: int | None = None
    misses: int | None = None
    keys: int | None = None
    hit_ratio: float | None = None


@router.get("/stats", response_model=CacheStats)
def get_stats(user: User = Depends(get_current_user)):
    return cache.stats()


@router.post("/clear")
def clear_cache(user: User = Depends(get_current_user)):
    removed = cache.clear()
    return {"cleared_keys": removed}
