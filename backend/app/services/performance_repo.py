# backend/app/services/performance_repo.py
"""Análisis de performance vía DMVs de SQL Server (Sprint 4).

Solo lectura. Requiere que el login tenga VIEW SERVER STATE para ver las DMVs
de servidor. Cada métrica se consulta de forma tolerante: si falla, devuelve
None en vez de romper todo.
"""
from sqlalchemy import text
from sqlalchemy.engine import Engine

# CPU del proceso SQL (última lectura del ring buffer del scheduler monitor)
_CPU_SQL = """
SELECT TOP 1 t.cpu AS cpu
FROM (
    SELECT record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int') AS cpu,
           record.value('(./Record/@id)[1]', 'bigint') AS rid
    FROM (
        SELECT CONVERT(xml, record) AS record
        FROM sys.dm_os_ring_buffers
        WHERE ring_buffer_type = N'RING_BUFFER_SCHEDULER_MONITOR'
          AND record LIKE '%<SystemHealth>%'
    ) AS rb
) AS t
ORDER BY t.rid DESC
"""

_SESSIONS_SQL = """
SELECT r.session_id AS session_id,
       s.login_name AS login_name,
       DB_NAME(r.database_id) AS database_name,
       r.status AS status,
       r.command AS command,
       r.cpu_time AS cpu_ms,
       r.total_elapsed_time AS elapsed_ms,
       NULLIF(r.blocking_session_id, 0) AS blocking_session_id,
       t.text AS query_text
FROM sys.dm_exec_requests r
JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
OUTER APPLY sys.dm_exec_sql_text(r.sql_handle) t
WHERE s.is_user_process = 1 AND r.session_id <> @@SPID
ORDER BY r.cpu_time DESC
"""

_TOPQ_SQL = """
SELECT TOP 5
       qs.execution_count AS execution_count,
       qs.total_worker_time / 1000 AS total_cpu_ms,
       (qs.total_worker_time / qs.execution_count) / 1000 AS avg_cpu_ms,
       t.text AS query_text
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) t
ORDER BY qs.total_worker_time DESC
"""


def _scalar(engine: Engine, sql: str):
    try:
        with engine.connect() as conn:
            return conn.execute(text(sql)).scalar()
    except Exception:
        return None


def _rows(engine: Engine, sql: str) -> list[dict]:
    with engine.connect() as conn:
        return [dict(r._mapping) for r in conn.execute(text(sql))]


def _clean(text_value):
    if not text_value:
        return None
    return " ".join(str(text_value).split())[:200]


def get_metrics(engine: Engine) -> dict:
    mem = None
    try:
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT total_physical_memory_kb AS total_kb, "
                "available_physical_memory_kb AS avail_kb FROM sys.dm_os_sys_memory"
            )).mappings().first()
        if row and row["total_kb"]:
            mem = round((1 - row["avail_kb"] / row["total_kb"]) * 100, 1)
    except Exception:
        mem = None

    return {
        "cpu_percent": _scalar(engine, _CPU_SQL),
        "memory_percent": mem,
        "sessions": _scalar(engine, "SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE is_user_process = 1"),
        "active_requests": _scalar(
            engine,
            "SELECT COUNT(*) FROM sys.dm_exec_requests r "
            "JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id "
            "WHERE s.is_user_process = 1 AND r.session_id <> @@SPID",
        ),
        "connections": _scalar(engine, "SELECT COUNT(*) FROM sys.dm_exec_connections"),
        "blocked": _scalar(engine, "SELECT COUNT(*) FROM sys.dm_exec_requests WHERE blocking_session_id <> 0"),
        "locks": _scalar(engine, "SELECT COUNT(*) FROM sys.dm_tran_locks"),
    }


def get_active_sessions(engine: Engine) -> list[dict]:
    rows = _rows(engine, _SESSIONS_SQL)
    for r in rows:
        r["query_text"] = _clean(r.get("query_text"))
    return rows


def get_top_queries(engine: Engine) -> list[dict]:
    rows = _rows(engine, _TOPQ_SQL)
    for r in rows:
        r["query_text"] = _clean(r.get("query_text"))
    return rows
