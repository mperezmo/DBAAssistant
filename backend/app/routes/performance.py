# backend/app/routes/performance.py
"""Análisis de performance POR CONEXIÓN (Sprint 4). Protegido por auth."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user
from app.models.auth import User
from app.models.performance import ActiveSession, PerfMetrics, TopQuery
from app.services import connections_repo, performance_repo

router = APIRouter(prefix="/performance", tags=["performance"])


def _engine_or_404(connection_id: str):
    engine = connections_repo.get_engine(connection_id)
    if engine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conexión no encontrada")
    return engine


def _read_error(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"No se pudo leer performance (¿el login tiene VIEW SERVER STATE?): {exc}",
    )


@router.get("/{connection_id}/metrics", response_model=PerfMetrics)
def metrics(connection_id: str, user: User = Depends(get_current_user)):
    engine = _engine_or_404(connection_id)
    try:
        return performance_repo.get_metrics(engine)
    except Exception as exc:  # noqa: BLE001
        raise _read_error(exc)


@router.get("/{connection_id}/sessions", response_model=list[ActiveSession])
def sessions(connection_id: str, user: User = Depends(get_current_user)):
    engine = _engine_or_404(connection_id)
    try:
        return performance_repo.get_active_sessions(engine)
    except Exception as exc:  # noqa: BLE001
        raise _read_error(exc)


@router.get("/{connection_id}/top-queries", response_model=list[TopQuery])
def top_queries(connection_id: str, user: User = Depends(get_current_user)):
    engine = _engine_or_404(connection_id)
    try:
        return performance_repo.get_top_queries(engine)
    except Exception as exc:  # noqa: BLE001
        raise _read_error(exc)
