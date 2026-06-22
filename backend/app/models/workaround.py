# backend/app/models/workaround.py
"""Modelos de la biblioteca de Workarounds (Sprint 10).

Un workaround es un playbook de remediación con dos SQL:
- `diagnose_sql`: SELECT de solo lectura (muestra qué se vería afectado).
- `apply_sql`: batch de remediación que ejecuta la acción real.
"""
from typing import Any

from pydantic import BaseModel


class Workaround(BaseModel):
    """Workaround del catálogo (built-in o custom) con sus estadísticas de uso."""
    key: str
    name: str
    description: str = ""
    category: str = "Mantenimiento"  # Performance | Espacio | Mantenimiento | Disponibilidad
    severity: str = "info"           # critical | warning | info
    kind: str = "sql"                # sql (T-SQL) | service (servicio Windows vía WinRM)
    requires_server_state: bool = False
    builtin: bool = True
    diagnose_sql: str | None = None
    apply_sql: str | None = None
    runs: int = 0
    last_run: str | None = None


class WorkaroundCreate(BaseModel):
    """Alta de un workaround custom (lo crea el DBA)."""
    key: str
    name: str
    description: str = ""
    category: str = "Mantenimiento"
    severity: str = "info"
    diagnose_sql: str
    apply_sql: str


class WorkaroundRunRequest(BaseModel):
    connection_id: str
    database: str = ""      # opcional para workarounds de servicio (no usan base)
    mode: str = "diagnose"  # diagnose (solo lectura) | apply (ejecuta la remediación)


class WorkaroundRunResponse(BaseModel):
    key: str
    mode: str
    columns: list[str] | None = None
    rows: list[list[Any]] | None = None
    affected_rows: int | None = None
    truncated: bool = False
    message: str | None = None
    elapsed_ms: int | None = None


class WorkaroundRunEntry(BaseModel):
    """Entrada del historial de ejecuciones."""
    id: str
    timestamp: str
    user: str
    key: str
    connection_id: str
    database: str
    mode: str
    success: bool
    affected_rows: int | None = None
    error: str | None = None


# ── Automatización por reglas (Sprint 10.1) ──────────────────────────────────

class WorkaroundRuleCreate(BaseModel):
    """Regla 'SI Y SOLO SI': corre el diagnóstico del workaround y, si detecta el
    problema (≥ min_rows), aplica la remediación. Reúne el qué, el dónde y el cuándo."""
    name: str
    workaround_key: str
    connection_id: str
    database: str = ""
    enabled: bool = True
    min_rows: int = 1            # umbral: filas de diagnóstico para considerar "hay problema"
    cooldown_seconds: int = 300  # no re-dispara antes de este lapso


class WorkaroundRuleUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    min_rows: int | None = None
    cooldown_seconds: int | None = None


class WorkaroundRule(WorkaroundRuleCreate):
    id: str
    last_triggered: str | None = None
    last_checked: str | None = None
    last_status: str | None = None


class RuleEvaluation(BaseModel):
    """Resultado de evaluar una regla (manual o por scheduler)."""
    rule_id: str
    name: str
    workaround_key: str
    checked: bool                # False si se saltó (deshabilitada / en cooldown)
    triggered: bool              # True si se aplicó la remediación
    problems: int = 0
    status: str | None = None
    error: str | None = None
