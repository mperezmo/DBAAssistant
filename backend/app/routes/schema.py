# backend/app/routes/schema.py
"""Análisis de metadata/esquema POR CONEXIÓN (Sprint 4). Protegido por auth."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user
from app.models.auth import User
from app.models.schema import DatabaseOverview, TableDetail, TableSummary
from app.services import connections_repo, schema_repo

router = APIRouter(prefix="/schema", tags=["schema"])


def _engine_or_404(connection_id: str):
    engine = connections_repo.get_engine(connection_id)
    if engine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conexión no encontrada")
    return engine


def _read_error(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"No se pudo leer la metadata: {exc}",
    )


@router.get("/{connection_id}/overview", response_model=DatabaseOverview)
def overview(connection_id: str, user: User = Depends(get_current_user)):
    engine = _engine_or_404(connection_id)
    try:
        return schema_repo.get_overview(engine)
    except Exception as exc:  # noqa: BLE001
        raise _read_error(exc)


@router.get("/{connection_id}/tables", response_model=list[TableSummary])
def tables(connection_id: str, user: User = Depends(get_current_user)):
    engine = _engine_or_404(connection_id)
    try:
        return schema_repo.list_tables(engine)
    except Exception as exc:  # noqa: BLE001
        raise _read_error(exc)


@router.get("/{connection_id}/tables/{schema_name}/{table_name}", response_model=TableDetail)
def table_detail(
    connection_id: str,
    schema_name: str,
    table_name: str,
    user: User = Depends(get_current_user),
):
    engine = _engine_or_404(connection_id)
    try:
        detail = schema_repo.get_table_detail(engine, schema_name, table_name)
    except Exception as exc:  # noqa: BLE001
        raise _read_error(exc)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tabla no encontrada")
    return detail
