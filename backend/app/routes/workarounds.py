# backend/app/routes/workarounds.py
"""Biblioteca de Workarounds (Sprint 10). Protegido por auth y auditado.

Cada workaround corre en dos modos sobre una base puntual:
- ``diagnose``: SELECT de solo lectura → muestra qué se vería afectado.
- ``apply``: ejecuta el batch de remediación real (auditado).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import get_current_user
from app.models.auth import User
from app.models.workaround import (
    Workaround, WorkaroundCreate, WorkaroundRunEntry, WorkaroundRunRequest,
    WorkaroundRunResponse,
)
from app.services import (
    audit_repo, cache, connections_repo, sql_executor, sql_validator, workarounds,
    workarounds_repo,
)

router = APIRouter(prefix="/workarounds", tags=["workarounds"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _resolve(key: str) -> dict | None:
    """Busca un workaround por key: primero built-in, luego custom."""
    return workarounds.get_builtin(key) or workarounds_repo.get_custom(key)


@router.get("", response_model=list[Workaround])
def list_workarounds(user: User = Depends(get_current_user)):
    """Catálogo completo (built-in + custom) con estadísticas de uso."""
    stats = workarounds_repo.run_stats()
    catalog = workarounds.list_builtins() + workarounds_repo.list_custom()
    out = []
    for w in catalog:
        s = stats.get(w["key"], {})
        out.append({**w, "runs": s.get("runs", 0), "last_run": s.get("last_run")})
    return out


@router.post("", response_model=Workaround, status_code=status.HTTP_201_CREATED)
def create_workaround(body: WorkaroundCreate, request: Request,
                      user: User = Depends(get_current_user)):
    if workarounds.get_builtin(body.key):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"La key '{body.key}' ya existe (built-in).")
    if not sql_validator.is_read_only(body.diagnose_sql):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="El SQL de diagnóstico debe ser de solo lectura (SELECT).")
    if not body.apply_sql.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="El SQL de remediación no puede estar vacío.")
    created = workarounds_repo.create_custom(body.model_dump())
    audit_repo.log(user.email or user.username, "workaround.create",
                   target=body.key, ip=_ip(request))
    return created


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workaround(key: str, request: Request, user: User = Depends(get_current_user)):
    if workarounds.get_builtin(key):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="No se pueden borrar workarounds built-in.")
    if not workarounds_repo.delete_custom(key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workaround no encontrado.")
    audit_repo.log(user.email or user.username, "workaround.delete", target=key, ip=_ip(request))


@router.get("/runs", response_model=list[WorkaroundRunEntry])
def list_runs(limit: int = 50, user: User = Depends(get_current_user)):
    return workarounds_repo.list_runs(min(limit, 200))


@router.post("/{key}/run", response_model=WorkaroundRunResponse)
def run_workaround(key: str, body: WorkaroundRunRequest, request: Request,
                   user: User = Depends(get_current_user)):
    wk = _resolve(key)
    if wk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workaround no encontrado.")

    engine = connections_repo.get_engine_for_db(body.connection_id, body.database)
    if engine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Conexión o base de datos no encontrada")

    actor = user.email or user.username
    mode = "apply" if body.mode == "apply" else "diagnose"
    try:
        if mode == "diagnose":
            columns, rows, truncated = sql_executor.run_select(engine, wk["diagnose_sql"])
            result = WorkaroundRunResponse(key=key, mode=mode, columns=columns, rows=rows,
                                           truncated=truncated)
            affected = None
        else:
            out = sql_executor.run_script(engine, wk["apply_sql"])
            affected = out["affected_rows"]
            cache.invalidate_connection(body.connection_id)  # mantenimiento → tamaños/planes cambian
            result = WorkaroundRunResponse(
                key=key, mode=mode, affected_rows=affected,
                message="Remediación aplicada.", elapsed_ms=out["elapsed_ms"],
            )
    except Exception as exc:  # noqa: BLE001
        workarounds_repo.log_run(actor, key, body.connection_id, body.database, mode,
                                 success=False, error=str(exc))
        audit_repo.log(actor, "workaround.run", target=f"{body.connection_id}/{body.database}",
                       detail=f"{key} · {mode} · error", ip=_ip(request))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error al ejecutar: {exc}")

    workarounds_repo.log_run(actor, key, body.connection_id, body.database, mode,
                             success=True, affected=affected)
    audit_repo.log(actor, "workaround.run", target=f"{body.connection_id}/{body.database}",
                   detail=f"{key} · {mode}", ip=_ip(request))
    return result
