# backend/app/models/performance.py
"""Modelos de análisis de performance (Sprint 4)."""
from pydantic import BaseModel


class PerfMetrics(BaseModel):
    cpu_percent: float | None = None
    memory_percent: float | None = None
    sessions: int | None = None
    active_requests: int | None = None
    connections: int | None = None
    blocked: int | None = None
    locks: int | None = None


class ActiveSession(BaseModel):
    session_id: int
    login_name: str | None = None
    database_name: str | None = None
    status: str | None = None
    command: str | None = None
    cpu_ms: int | None = None
    elapsed_ms: int | None = None
    blocking_session_id: int | None = None
    query_text: str | None = None


class TopQuery(BaseModel):
    query_text: str | None = None
    execution_count: int
    total_cpu_ms: int
    avg_cpu_ms: int
