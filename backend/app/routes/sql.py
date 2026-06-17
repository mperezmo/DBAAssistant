# backend/app/routes/sql.py
"""Generación y ejecución controlada de SQL (Sprint 5). Protegido por auth."""
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import get_current_user
from app.models.auth import User
from app.models.sql import (
    ExecuteRequest, ExecuteResponse, GenerateRequest, GenerateResponse, QueryHistoryEntry,
)
from app.services import (
    audit_repo, claude, connections_repo, query_history_repo, schema_repo,
    sql_executor, sql_validator,
)

router = APIRouter(prefix="/sql", tags=["sql"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/generate", response_model=GenerateResponse)
def generate(body: GenerateRequest, user: User = Depends(get_current_user)):
    if not claude.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Claude no está configurado: falta ANTHROPIC_API_KEY",
        )
    schema_context = None
    if body.connection_id and body.database:
        try:
            engine = connections_repo.get_engine_for_db(body.connection_id, body.database)
            if engine is not None:
                tbls = schema_repo.list_tables(engine)
                schema_context = ", ".join(f"{t['schema_name']}.{t['table_name']}" for t in tbls[:50])
        except Exception:  # noqa: BLE001
            schema_context = None
    try:
        sql = claude.generate_sql(body.prompt, schema_context)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Error al generar SQL: {exc}")
    return GenerateResponse(sql=sql)


@router.post("/execute", response_model=ExecuteResponse)
def execute(body: ExecuteRequest, request: Request, user: User = Depends(get_current_user)):
    engine = connections_repo.get_engine_for_db(body.connection_id, body.database)
    if engine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conexión o base de datos no encontrada")

    actor = user.email or user.username
    warnings = sql_validator.analyze(body.sql)
    try:
        result = sql_executor.run(engine, body.sql, body.mode)
    except Exception as exc:  # noqa: BLE001
        query_history_repo.add(actor, body.connection_id, body.database, body.sql, success=False, error=str(exc))
        audit_repo.log(actor, "query.execute", target=f"{body.connection_id}/{body.database}",
                       detail="error", ip=_ip(request))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error al ejecutar: {exc}")

    result["warnings"] = warnings
    query_history_repo.add(actor, body.connection_id, body.database, body.sql, kind=result["kind"],
                           affected_rows=result.get("affected_rows"), committed=result.get("committed", False))
    audit_repo.log(actor, "query.execute", target=f"{body.connection_id}/{body.database}",
                   detail=f"{result['kind']} · {body.mode} · committed={result.get('committed')}", ip=_ip(request))
    return result


@router.get("/history", response_model=list[QueryHistoryEntry])
def history(limit: int = 50, user: User = Depends(get_current_user)):
    return query_history_repo.list_recent(min(limit, 200))
