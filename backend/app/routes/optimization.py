# backend/app/routes/optimization.py
"""Recomendaciones de optimización de índices POR CONEXIÓN+BASE (Sprint 6)."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user
from app.models.auth import User
from app.models.optimization import MissingIndex, UnusedIndex
from app.services import connections_repo, optimization_repo

router = APIRouter(prefix="/optimization", tags=["optimization"])


def _engine_or_404(connection_id: str, database: str):
    try:
        engine = connections_repo.get_engine_for_db(connection_id, database)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"No se pudo conectar: {exc}")
    if engine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conexión o base de datos no encontrada")
    return engine


def _read_error(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"No se pudo leer (¿el login tiene VIEW SERVER STATE?): {exc}",
    )


@router.get("/{connection_id}/{database}/missing-indexes", response_model=list[MissingIndex])
def missing_indexes(connection_id: str, database: str, user: User = Depends(get_current_user)):
    engine = _engine_or_404(connection_id, database)
    try:
        return optimization_repo.missing_indexes(engine)
    except Exception as exc:  # noqa: BLE001
        raise _read_error(exc)


@router.get("/{connection_id}/{database}/unused-indexes", response_model=list[UnusedIndex])
def unused_indexes(connection_id: str, database: str, user: User = Depends(get_current_user)):
    engine = _engine_or_404(connection_id, database)
    try:
        return optimization_repo.unused_indexes(engine)
    except Exception as exc:  # noqa: BLE001
        raise _read_error(exc)
