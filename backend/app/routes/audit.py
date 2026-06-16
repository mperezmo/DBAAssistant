# backend/app/routes/audit.py
"""Bitácora de auditoría (Sprint 4). Protegida por auth."""
from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models.audit import AuditEntry
from app.models.auth import User
from app.services import audit_repo

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditEntry])
def list_audit(
    limit: int = 100,
    action: str | None = None,
    user: User = Depends(get_current_user),
):
    return audit_repo.list_recent(limit=min(limit, 500), action=action)
