# backend/app/routes/connections.py
"""CRUD de conexiones a SQL Server (Sprint 4). Protegidas por auth."""
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import get_current_user
from app.models.auth import User
from app.models.connection import Connection, ConnectionCreate, ConnectionTestResult
from app.services import audit_repo, connections_repo

router = APIRouter(prefix="/connections", tags=["connections"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("", response_model=list[Connection])
def list_connections(user: User = Depends(get_current_user)):
    return connections_repo.list_all()


@router.get("/{connection_id}/databases", response_model=list[str])
def list_databases(connection_id: str, user: User = Depends(get_current_user)):
    try:
        dbs = connections_repo.list_databases(connection_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudieron listar las bases: {exc}",
        )
    if dbs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conexión no encontrada")
    return dbs


@router.post("", response_model=Connection, status_code=status.HTTP_201_CREATED)
def create_connection(body: ConnectionCreate, request: Request, user: User = Depends(get_current_user)):
    created = connections_repo.create(body.model_dump())
    audit_repo.log(user.email or user.username, "connection.create",
                   target=created["name"], detail=f"{body.host}:{body.port}", ip=_ip(request))
    return created


@router.post("/test", response_model=ConnectionTestResult)
def test_connection(body: ConnectionCreate, user: User = Depends(get_current_user)):
    ok, detail, server = connections_repo.test(body.model_dump())
    return ConnectionTestResult(ok=ok, server=server, detail=detail)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(connection_id: str, request: Request, user: User = Depends(get_current_user)):
    if not connections_repo.delete(connection_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conexión no encontrada")
    audit_repo.log(user.email or user.username, "connection.delete",
                   target=connection_id, ip=_ip(request))
