# backend/app/models/audit.py
"""Modelos de auditoría (Sprint 4)."""
from pydantic import BaseModel


class AuditEntry(BaseModel):
    id: str
    timestamp: str  # ISO 8601
    user: str
    action: str
    target: str | None = None
    detail: str | None = None
    ip: str | None = None
