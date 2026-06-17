# backend/app/models/optimization.py
"""Modelos de optimización de queries / índices (Sprint 6)."""
from pydantic import BaseModel


class MissingIndex(BaseModel):
    schema_name: str
    table_name: str
    impact: float | None = None
    avg_impact_pct: float | None = None
    uses: int | None = None
    equality_columns: str | None = None
    inequality_columns: str | None = None
    included_columns: str | None = None
    create_statement: str


class UnusedIndex(BaseModel):
    schema_name: str
    table_name: str
    index_name: str
    type_desc: str
    user_seeks: int
    user_scans: int
    user_lookups: int
    user_updates: int
    drop_statement: str
