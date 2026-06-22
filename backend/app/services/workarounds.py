# backend/app/services/workarounds.py
"""Catálogo built-in de Workarounds (Sprint 10).

Cada workaround es un playbook de remediación pre-aprobado. Trae dos SQL:

- ``diagnose_sql``: SELECT de SOLO LECTURA que muestra qué se vería afectado
  (sesiones bloqueantes, índices fragmentados, archivos de log, etc.).
- ``apply_sql``: un único batch T-SQL (SIN ``GO``) que ejecuta la remediación.
  Los batches que iteran usan ``BEGIN TRY … END TRY BEGIN CATCH … END CATCH``
  por ítem para tolerar fallos parciales.

Los workarounds corren sobre una base puntual (engine por conexión+base). Las DMVs
de servidor (sesiones, plan cache) requieren ``VIEW SERVER STATE`` en el login.
"""

# ── Diagnósticos (solo lectura) ──────────────────────────────────────────────

_DIAG_KILL_BLOCKING = """
SELECT r.blocking_session_id AS blocker_spid,
       COUNT(*)              AS blocked_count,
       MAX(r.wait_time) / 1000 AS max_wait_seconds
FROM sys.dm_exec_requests AS r
WHERE r.blocking_session_id <> 0
GROUP BY r.blocking_session_id
ORDER BY blocked_count DESC
""".strip()

_DIAG_REBUILD_INDEXES = """
SELECT TOP 50
       OBJECT_SCHEMA_NAME(ips.object_id) AS schema_name,
       OBJECT_NAME(ips.object_id)        AS table_name,
       i.name                            AS index_name,
       CAST(ips.avg_fragmentation_in_percent AS DECIMAL(5, 2)) AS frag_pct,
       ips.page_count
FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') AS ips
JOIN sys.indexes AS i
  ON i.object_id = ips.object_id AND i.index_id = ips.index_id
WHERE ips.avg_fragmentation_in_percent > 30
  AND ips.page_count > 100
  AND i.name IS NOT NULL
ORDER BY ips.avg_fragmentation_in_percent DESC
""".strip()

_DIAG_UPDATE_STATS = """
SELECT TOP 50
       OBJECT_SCHEMA_NAME(s.object_id) AS schema_name,
       OBJECT_NAME(s.object_id)        AS table_name,
       s.name                          AS stat_name,
       sp.modification_counter,
       sp.rows
FROM sys.stats AS s
CROSS APPLY sys.dm_db_stats_properties(s.object_id, s.stats_id) AS sp
WHERE sp.modification_counter > 0
  AND OBJECTPROPERTY(s.object_id, 'IsUserTable') = 1
ORDER BY sp.modification_counter DESC
""".strip()

_DIAG_SHRINK_LOG = """
SELECT name                                        AS log_file,
       CAST(size / 128.0 AS DECIMAL(10, 2))        AS size_mb,
       CAST(FILEPROPERTY(name, 'SpaceUsed') / 128.0 AS DECIMAL(10, 2)) AS used_mb
FROM sys.database_files
WHERE type = 1
""".strip()

_DIAG_CLEAR_PLAN_CACHE = """
SELECT COUNT(*) AS cached_plans,
       CAST(SUM(CAST(cp.size_in_bytes AS BIGINT)) / 1048576.0 AS DECIMAL(10, 2)) AS cache_mb
FROM sys.dm_exec_cached_plans AS cp
CROSS APPLY sys.dm_exec_plan_attributes(cp.plan_handle) AS pa
WHERE pa.attribute = 'dbid'
  AND CAST(pa.value AS INT) = DB_ID()
""".strip()

_DIAG_CHECKPOINT = """
SELECT DB_NAME()           AS database_name,
       recovery_model_desc,
       log_reuse_wait_desc
FROM sys.databases
WHERE database_id = DB_ID()
""".strip()

# ── Remediaciones (batches, sin GO) ──────────────────────────────────────────

_APPLY_KILL_BLOCKING = """
DECLARE @spid INT, @sql NVARCHAR(50);
DECLARE blockers CURSOR LOCAL FAST_FORWARD FOR
    SELECT DISTINCT blocking_session_id
    FROM sys.dm_exec_requests
    WHERE blocking_session_id <> 0;
OPEN blockers;
FETCH NEXT FROM blockers INTO @spid;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @sql = N'KILL ' + CAST(@spid AS NVARCHAR(10));
    BEGIN TRY EXEC sp_executesql @sql; END TRY BEGIN CATCH END CATCH;
    FETCH NEXT FROM blockers INTO @spid;
END
CLOSE blockers;
DEALLOCATE blockers;
""".strip()

_APPLY_REBUILD_INDEXES = """
DECLARE @schema SYSNAME, @table SYSNAME, @index SYSNAME, @sql NVARCHAR(MAX);
DECLARE frag CURSOR LOCAL FAST_FORWARD FOR
    SELECT OBJECT_SCHEMA_NAME(ips.object_id),
           OBJECT_NAME(ips.object_id),
           i.name
    FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') AS ips
    JOIN sys.indexes AS i
      ON i.object_id = ips.object_id AND i.index_id = ips.index_id
    WHERE ips.avg_fragmentation_in_percent > 30
      AND ips.page_count > 100
      AND i.name IS NOT NULL;
OPEN frag;
FETCH NEXT FROM frag INTO @schema, @table, @index;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @sql = N'ALTER INDEX ' + QUOTENAME(@index) + N' ON '
             + QUOTENAME(@schema) + N'.' + QUOTENAME(@table) + N' REBUILD;';
    BEGIN TRY EXEC sp_executesql @sql; END TRY BEGIN CATCH END CATCH;
    FETCH NEXT FROM frag INTO @schema, @table, @index;
END
CLOSE frag;
DEALLOCATE frag;
""".strip()

_APPLY_UPDATE_STATS = "EXEC sp_updatestats;"

_APPLY_SHRINK_LOG = """
DECLARE @name SYSNAME, @sql NVARCHAR(200);
DECLARE logs CURSOR LOCAL FAST_FORWARD FOR
    SELECT name FROM sys.database_files WHERE type = 1;
OPEN logs;
FETCH NEXT FROM logs INTO @name;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @sql = N'DBCC SHRINKFILE(' + QUOTENAME(@name, '''') + N', 64) WITH NO_INFOMSGS;';
    BEGIN TRY EXEC sp_executesql @sql; END TRY BEGIN CATCH END CATCH;
    FETCH NEXT FROM logs INTO @name;
END
CLOSE logs;
DEALLOCATE logs;
""".strip()

_APPLY_CLEAR_PLAN_CACHE = "DECLARE @dbid INT = DB_ID(); DBCC FLUSHPROCINDB(@dbid) WITH NO_INFOMSGS;"

_APPLY_CHECKPOINT = "CHECKPOINT;"


BUILTINS: list[dict] = [
    {
        "key": "kill_blocking_sessions",
        "name": "Liberar sesiones bloqueantes",
        "description": "Detecta sesiones que están bloqueando a otras y las termina con KILL.",
        "category": "Performance",
        "severity": "critical",
        "requires_server_state": True,
        "diagnose_sql": _DIAG_KILL_BLOCKING,
        "apply_sql": _APPLY_KILL_BLOCKING,
    },
    {
        "key": "rebuild_fragmented_indexes",
        "name": "Reconstruir índices fragmentados",
        "description": "REBUILD sobre índices con fragmentación > 30% y más de 100 páginas.",
        "category": "Performance",
        "severity": "warning",
        "requires_server_state": False,
        "diagnose_sql": _DIAG_REBUILD_INDEXES,
        "apply_sql": _APPLY_REBUILD_INDEXES,
    },
    {
        "key": "update_stale_statistics",
        "name": "Actualizar estadísticas obsoletas",
        "description": "UPDATE STATISTICS sobre tablas de usuario con cambios pendientes (sp_updatestats).",
        "category": "Mantenimiento",
        "severity": "info",
        "requires_server_state": False,
        "diagnose_sql": _DIAG_UPDATE_STATS,
        "apply_sql": _APPLY_UPDATE_STATS,
    },
    {
        "key": "shrink_log",
        "name": "Shrink de log de transacciones",
        "description": "Reduce el/los archivo(s) de log de la base a un tamaño objetivo (DBCC SHRINKFILE 64 MB).",
        "category": "Espacio",
        "severity": "warning",
        "requires_server_state": False,
        "diagnose_sql": _DIAG_SHRINK_LOG,
        "apply_sql": _APPLY_SHRINK_LOG,
    },
    {
        "key": "clear_plan_cache",
        "name": "Limpiar plan cache de la base",
        "description": "DBCC FLUSHPROCINDB selectivo: descarta los planes cacheados de esta base.",
        "category": "Performance",
        "severity": "warning",
        "requires_server_state": True,
        "diagnose_sql": _DIAG_CLEAR_PLAN_CACHE,
        "apply_sql": _APPLY_CLEAR_PLAN_CACHE,
    },
    {
        "key": "force_checkpoint",
        "name": "Forzar checkpoint manual",
        "description": "Ejecuta CHECKPOINT para volcar las páginas sucias del buffer pool al disco.",
        "category": "Mantenimiento",
        "severity": "info",
        "requires_server_state": False,
        "diagnose_sql": _DIAG_CHECKPOINT,
        "apply_sql": _APPLY_CHECKPOINT,
    },
]

_BY_KEY = {w["key"]: w for w in BUILTINS}


def list_builtins() -> list[dict]:
    """Workarounds del catálogo fijo (copias, marcadas como builtin)."""
    return [{**w, "builtin": True} for w in BUILTINS]


def get_builtin(key: str) -> dict | None:
    w = _BY_KEY.get(key)
    return {**w, "builtin": True} if w else None
