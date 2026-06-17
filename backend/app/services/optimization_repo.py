# backend/app/services/optimization_repo.py
"""Recomendaciones de optimización de índices vía DMVs (Sprint 6).

Solo lectura. Requiere VIEW SERVER STATE. Las DMVs de índices faltantes/uso se
acumulan desde el último reinicio del motor.
"""
import re

from sqlalchemy import text
from sqlalchemy.engine import Engine

_MISSING_SQL = """
SELECT TOP 20
    ROUND(s.avg_total_user_cost * s.avg_user_impact * (s.user_seeks + s.user_scans), 0) AS impact,
    s.user_seeks + s.user_scans AS uses,
    CAST(s.avg_user_impact AS DECIMAL(6, 1)) AS avg_impact_pct,
    OBJECT_SCHEMA_NAME(d.object_id, d.database_id) AS schema_name,
    OBJECT_NAME(d.object_id, d.database_id) AS table_name,
    d.equality_columns AS equality_columns,
    d.inequality_columns AS inequality_columns,
    d.included_columns AS included_columns
FROM sys.dm_db_missing_index_group_stats s
JOIN sys.dm_db_missing_index_groups g ON s.group_handle = g.index_group_handle
JOIN sys.dm_db_missing_index_details d ON g.index_handle = d.index_handle
WHERE d.database_id = DB_ID()
ORDER BY impact DESC
"""

_UNUSED_SQL = """
SELECT
    OBJECT_SCHEMA_NAME(i.object_id) AS schema_name,
    OBJECT_NAME(i.object_id) AS table_name,
    i.name AS index_name,
    i.type_desc AS type_desc,
    ISNULL(us.user_seeks, 0) AS user_seeks,
    ISNULL(us.user_scans, 0) AS user_scans,
    ISNULL(us.user_lookups, 0) AS user_lookups,
    ISNULL(us.user_updates, 0) AS user_updates
FROM sys.indexes i
JOIN sys.objects o ON i.object_id = o.object_id
LEFT JOIN sys.dm_db_index_usage_stats us
    ON us.object_id = i.object_id AND us.index_id = i.index_id AND us.database_id = DB_ID()
WHERE o.is_ms_shipped = 0
  AND i.type_desc = 'NONCLUSTERED'
  AND i.is_primary_key = 0
  AND i.is_unique_constraint = 0
  AND (ISNULL(us.user_seeks, 0) + ISNULL(us.user_scans, 0) + ISNULL(us.user_lookups, 0)) = 0
ORDER BY ISNULL(us.user_updates, 0) DESC, table_name
"""


def _rows(engine: Engine, sql: str) -> list[dict]:
    with engine.connect() as conn:
        return [dict(r._mapping) for r in conn.execute(text(sql))]


def _build_create(r: dict) -> str:
    keys = [c for c in (r.get("equality_columns"), r.get("inequality_columns")) if c]
    key_cols = ", ".join(keys)
    raw = r.get("equality_columns") or r.get("inequality_columns") or "idx"
    suffix = re.sub(r"[^\w]+", "_", raw).strip("_")[:40] or "idx"
    name = f"IX_{r['table_name']}_{suffix}"
    stmt = f"CREATE NONCLUSTERED INDEX [{name}] ON [{r['schema_name']}].[{r['table_name']}] ({key_cols})"
    if r.get("included_columns"):
        stmt += f" INCLUDE ({r['included_columns']})"
    return stmt + ";"


def missing_indexes(engine: Engine) -> list[dict]:
    rows = _rows(engine, _MISSING_SQL)
    for r in rows:
        if r.get("impact") is not None:
            r["impact"] = float(r["impact"])
        if r.get("avg_impact_pct") is not None:
            r["avg_impact_pct"] = float(r["avg_impact_pct"])
        r["create_statement"] = _build_create(r)
    return rows


def unused_indexes(engine: Engine) -> list[dict]:
    rows = _rows(engine, _UNUSED_SQL)
    for r in rows:
        r["drop_statement"] = f"DROP INDEX [{r['index_name']}] ON [{r['schema_name']}].[{r['table_name']}];"
    return rows
