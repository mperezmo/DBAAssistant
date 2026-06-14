# backend/app/routes/schema.py
"""Rutas de análisis de metadata/esquema (Sprint 4). Protegidas por auth."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user
from app.models.auth import User
from app.models.schema import DatabaseOverview, TableDetail, TableSummary
from app.services import schema_repo

router = APIRouter(prefix="/schema", tags=["schema"])


def _read_error(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"No se pudo leer la metadata de SQL Server: {exc}",
    )


@router.get("/overview", response_model=DatabaseOverview)
def overview(user: User = Depends(get_current_user)):
    try:
        return schema_repo.get_overview()
    except Exception as exc:  # noqa: BLE001
        raise _read_error(exc)


@router.get("/tables", response_model=list[TableSummary])
def tables(user: User = Depends(get_current_user)):
    try:
        return schema_repo.list_tables()
    except Exception as exc:  # noqa: BLE001
        raise _read_error(exc)


@router.get("/tables/{schema_name}/{table_name}", response_model=TableDetail)
def table_detail(schema_name: str, table_name: str, user: User = Depends(get_current_user)):
    try:
        detail = schema_repo.get_table_detail(schema_name, table_name)
    except Exception as exc:  # noqa: BLE001
        raise _read_error(exc)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tabla no encontrada")
    return detail
