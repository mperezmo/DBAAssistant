# backend/app/routes/context.py
"""Contexto de negocio por conexión+base (Sprint 9). Protegido por auth."""
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import get_current_user
from app.models.auth import User
from app.models.context import DatabaseContext, TableContext, TableContextEntry
from app.services import audit_repo, cache, claude, connections_repo, context_repo, schema_repo

router = APIRouter(prefix="/context", tags=["context"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/{connection_id}/{database}", response_model=DatabaseContext)
def read_db_context(connection_id: str, database: str, user: User = Depends(get_current_user)):
    return context_repo.get_db_context(connection_id, database)


@router.put("/{connection_id}/{database}", response_model=DatabaseContext)
def write_db_context(connection_id: str, database: str, body: DatabaseContext,
                     request: Request, user: User = Depends(get_current_user)):
    context_repo.set_db_context(connection_id, database, body.model_dump())
    cache.invalidate_connection(connection_id)  # el contexto cambia → refrescar IA
    audit_repo.log(user.email or user.username, "context.update",
                   target=f"{connection_id}/{database}", ip=_ip(request))
    return body


@router.post("/{connection_id}/{database}/refine", response_model=DatabaseContext)
def refine_context(connection_id: str, database: str, body: DatabaseContext,
                   user: User = Depends(get_current_user)):
    """Procesa el contexto 'en criollo' con IA → versión profesional mapeada al
    esquema real. No lo guarda: lo devuelve para que el usuario revise y confirme."""
    if not claude.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Claude no está configurado: falta ANTHROPIC_API_KEY",
        )
    summary = None
    try:
        engine = connections_repo.get_engine_for_db(connection_id, database)
        if engine is not None:
            summary = schema_repo.schema_summary(engine)
    except Exception:  # noqa: BLE001
        summary = None
    try:
        return claude.refine_business_context(body.model_dump(), summary)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Error al procesar con IA: {exc}")


@router.get("/{connection_id}/{database}/tables", response_model=list[TableContextEntry])
def list_table_contexts(connection_id: str, database: str, user: User = Depends(get_current_user)):
    return context_repo.list_table_contexts(connection_id, database)


@router.get("/{connection_id}/{database}/tables/{schema}/{table}", response_model=TableContext)
def read_table_context(connection_id: str, database: str, schema: str, table: str,
                       user: User = Depends(get_current_user)):
    return context_repo.get_table_context(connection_id, database, schema, table)


@router.put("/{connection_id}/{database}/tables/{schema}/{table}", response_model=TableContext)
def write_table_context(connection_id: str, database: str, schema: str, table: str,
                        body: TableContext, request: Request, user: User = Depends(get_current_user)):
    context_repo.set_table_context(connection_id, database, schema, table, body.model_dump())
    audit_repo.log(user.email or user.username, "context.update",
                   target=f"{connection_id}/{database}/{schema}.{table}", ip=_ip(request))
    return body
