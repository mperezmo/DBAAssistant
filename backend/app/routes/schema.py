# backend/app/routes/schema.py
"""Análisis de metadata/esquema POR CONEXIÓN Y BASE (Sprint 4/6).

Con caché Redis (Sprint 6): los resultados se cachean por (conexión, base);
`refresh=true` saltea la caché y la repuebla.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import get_current_user
from app.models.auth import User
from app.models.schema import DatabaseOverview, TableDetail, TableSummary
from app.services import audit_repo, cache, connections_repo, schema_repo

router = APIRouter(prefix="/schema", tags=["schema"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _read_error(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"No se pudo leer la metadata: {exc}",
    )


def _engine_for(connection_id: str, database: str):
    try:
        engine = connections_repo.get_engine_for_db(connection_id, database)
    except Exception as exc:  # noqa: BLE001
        raise _read_error(exc)
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conexión o base de datos no encontrada",
        )
    return engine


@router.get("/{connection_id}/{database}/overview", response_model=DatabaseOverview)
def overview(connection_id: str, database: str, request: Request,
             refresh: bool = False, user: User = Depends(get_current_user)):
    audit_repo.log(user.email or user.username, "schema.view",
                   target=f"{connection_id}/{database}", ip=_ip(request))
    key = f"cache:data:overview:{connection_id}:{database}"
    if not refresh:
        cached = cache.get_json(key)
        if cached is not None:
            return cached
    engine = _engine_for(connection_id, database)
    try:
        result = schema_repo.get_overview(engine)
    except Exception as exc:  # noqa: BLE001
        raise _read_error(exc)
    cache.set_json(key, result)
    return result


@router.get("/{connection_id}/{database}/tables", response_model=list[TableSummary])
def tables(connection_id: str, database: str,
           refresh: bool = False, user: User = Depends(get_current_user)):
    key = f"cache:data:tables:{connection_id}:{database}"
    if not refresh:
        cached = cache.get_json(key)
        if cached is not None:
            return cached
    engine = _engine_for(connection_id, database)
    try:
        result = schema_repo.list_tables(engine)
    except Exception as exc:  # noqa: BLE001
        raise _read_error(exc)
    cache.set_json(key, result)
    return result


@router.get("/{connection_id}/{database}/tables/{schema_name}/{table_name}", response_model=TableDetail)
def table_detail(connection_id: str, database: str, schema_name: str, table_name: str,
                 refresh: bool = False, user: User = Depends(get_current_user)):
    key = f"cache:data:table:{connection_id}:{database}:{schema_name}:{table_name}"
    if not refresh:
        cached = cache.get_json(key)
        if cached is not None:
            return cached
    engine = _engine_for(connection_id, database)
    try:
        detail = schema_repo.get_table_detail(engine, schema_name, table_name)
    except Exception as exc:  # noqa: BLE001
        raise _read_error(exc)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tabla no encontrada")
    cache.set_json(key, detail)
    return detail
