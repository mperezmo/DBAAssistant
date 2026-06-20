# backend/app/routes/context.py
"""Contexto de negocio por conexión+base (Sprint 9). Protegido por auth."""
from fastapi import APIRouter, Depends, Request

from app.dependencies import get_current_user
from app.models.auth import User
from app.models.context import DatabaseContext, TableContext, TableContextEntry
from app.services import audit_repo, cache, context_repo

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
