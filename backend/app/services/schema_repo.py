# backend/app/services/schema_repo.py
"""Introspección de metadata de SQL Server (Sprint 4).

Opera sobre un engine de SQLAlchemy arbitrario (la conexión que el usuario
seleccione). Lee los catálogos del sistema (sys.*). Solo lectura.
"""
from sqlalchemy import text
from sqlalchemy.engine import Engine

_TABLES_SQL = """
SELECT s.name AS schema_name,
       t.name AS table_name,
       p.rows AS row_count,
       (SELECT ISNULL(SUM(a.total_pages), 0) * 8
          FROM sys.partitions pp
          JOIN sys.allocation_units a ON pp.partition_id = a.container_id
         WHERE pp.object_id = t.object_id) AS size_kb,
       (SELECT COUNT(*) FROM sys.columns c WHERE c.object_id = t.object_id) AS column_count,
       (SELECT COUNT(*) FROM sys.indexes i WHERE i.object_id = t.object_id AND i.type > 0) AS index_count
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0, 1)
ORDER BY size_kb DESC, t.name
"""

_COLUMNS_SQL = """
SELECT c.name AS name,
       ty.name AS data_type,
       c.max_length AS max_length,
       c.is_nullable AS is_nullable,
       CASE WHEN pk.column_id IS NOT NULL THEN 1 ELSE 0 END AS is_primary_key
FROM sys.columns c
JOIN sys.types ty ON c.user_type_id = ty.user_type_id
LEFT JOIN (
    SELECT ic.object_id, ic.column_id
    FROM sys.index_columns ic
    JOIN sys.indexes i ON ic.object_id = i.object_id AND ic.index_id = i.index_id
    WHERE i.is_primary_key = 1
) pk ON pk.object_id = c.object_id AND pk.column_id = c.column_id
WHERE c.object_id = OBJECT_ID(:tbl)
ORDER BY c.column_id
"""

_INDEXES_SQL = """
SELECT i.name AS name, i.type_desc AS type_desc,
       i.is_unique AS is_unique, i.is_primary_key AS is_primary_key
FROM sys.indexes i
WHERE i.object_id = OBJECT_ID(:tbl) AND i.type > 0
ORDER BY i.is_primary_key DESC, i.name
"""

_FKS_SQL = """
SELECT fk.name AS name,
       OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS ref_schema,
       OBJECT_NAME(fk.referenced_object_id) AS ref_table
FROM sys.foreign_keys fk
WHERE fk.parent_object_id = OBJECT_ID(:tbl)
ORDER BY fk.name
"""


def _rows(engine: Engine, sql: str, params: dict | None = None) -> list[dict]:
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return [dict(r._mapping) for r in result]


def get_overview(engine: Engine) -> dict:
    table_count = _rows(engine, "SELECT COUNT(*) AS c FROM sys.tables")[0]["c"]
    size_kb = _rows(
        engine,
        """SELECT ISNULL(SUM(a.total_pages), 0) * 8 AS kb
             FROM sys.allocation_units a
             JOIN sys.partitions p ON a.container_id = p.partition_id
             JOIN sys.tables t ON p.object_id = t.object_id""",
    )[0]["kb"]
    info = _rows(engine, "SELECT DB_NAME() AS d, CAST(@@SERVERNAME AS NVARCHAR(256)) AS s")[0]
    return {
        "server": info["s"],
        "database": info["d"],
        "table_count": int(table_count),
        "total_size_kb": int(size_kb),
    }


def list_tables(engine: Engine) -> list[dict]:
    return _rows(engine, _TABLES_SQL)


_SCHEMA_SUMMARY_SQL = """
SELECT TABLE_SCHEMA AS s, TABLE_NAME AS t, COLUMN_NAME AS c
FROM INFORMATION_SCHEMA.COLUMNS
ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
"""


def schema_summary(engine: Engine, max_tables: int = 60) -> str:
    """Resumen compacto del esquema: 'schema.tabla(col1, col2, ...)' por línea.

    Para anclar a la IA (generación/refinamiento/chat) en los objetos REALES.
    """
    rows = _rows(engine, _SCHEMA_SUMMARY_SQL)
    tables: dict[str, list[str]] = {}
    for r in rows:
        tables.setdefault(f"{r['s']}.{r['t']}", []).append(r["c"])
    lines = [f"{name}({', '.join(cols)})" for name, cols in list(tables.items())[:max_tables]]
    return "\n".join(lines)


def get_table_detail(engine: Engine, schema_name: str, table_name: str) -> dict | None:
    tbl = f"{schema_name}.{table_name}"
    oid = _rows(engine, "SELECT OBJECT_ID(:t) AS oid", {"t": tbl})[0]["oid"]
    if oid is None:
        return None
    return {
        "schema_name": schema_name,
        "table_name": table_name,
        "columns": _rows(engine, _COLUMNS_SQL, {"tbl": tbl}),
        "indexes": _rows(engine, _INDEXES_SQL, {"tbl": tbl}),
        "foreign_keys": _rows(engine, _FKS_SQL, {"tbl": tbl}),
    }
