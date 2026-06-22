# backend/app/models/sql.py
"""Modelos de generación y ejecución de SQL (Sprint 5)."""
from typing import Any

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    prompt: str
    connection_id: str | None = None
    database: str | None = None


class GenerateResponse(BaseModel):
    sql: str


class ExecuteRequest(BaseModel):
    connection_id: str
    database: str
    sql: str
    mode: str = "preview"  # preview (rollback) | apply (commit). Ignorado en SELECT.


class ExecuteResponse(BaseModel):
    kind: str  # "select" | "write"
    columns: list[str] | None = None
    rows: list[list[Any]] | None = None
    affected_rows: int | None = None
    committed: bool = False
    warnings: list[str] = []
    elapsed_ms: int | None = None


class ExportRequest(BaseModel):
    connection_id: str
    database: str
    sql: str


class QueryHistoryEntry(BaseModel):
    id: str
    timestamp: str
    user: str
    connection_id: str
    database: str
    sql: str
    kind: str | None = None
    affected_rows: int | None = None
    committed: bool = False
    success: bool
    error: str | None = None
