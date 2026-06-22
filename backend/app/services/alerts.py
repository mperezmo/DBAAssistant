# backend/app/services/alerts.py
"""Motor de Alertas (Sprint 11).

Evalúa las reglas habilitadas contra las métricas en vivo:
- instancia: ``performance_repo.get_metrics`` (DMVs de servidor, una vez por conexión).
- base: ``log_used_pct`` (sys.database_files de esa base).
- disponibilidad: ``service_down`` (WinRM) / ``instance_unreachable`` (no conecta).

Si se cruza el umbral, levanta/actualiza una alerta. Si la regla tiene
``auto_remediate`` y el valor llega al ``auto_threshold`` (límite máximo), ejecuta
el workaround sugerido (auditado ``alert.auto_remediate``). Si la condición se
limpia, resuelve la alerta. Es la ÚNICA vía de auto-remediación del sistema.
"""
from datetime import datetime, timezone

from sqlalchemy import text

from app.services import (
    alerts_repo, audit_repo, connections_repo, host_control, performance_repo,
    workaround_exec, workarounds_repo,
)

_OPS = {
    "gt": lambda v, t: v > t,
    "gte": lambda v, t: v >= t,
    "lt": lambda v, t: v < t,
    "lte": lambda v, t: v <= t,
}
_OP_SYM = {"gt": ">", "gte": "≥", "lt": "<", "lte": "≤"}

_INSTANCE_METRICS = {
    "cpu_percent", "memory_percent", "sessions", "active_requests",
    "connections", "blocked", "locks",
}

_LABEL = {
    "cpu_percent": "CPU %", "memory_percent": "Memoria %", "sessions": "Sesiones",
    "active_requests": "Requests activos", "connections": "Conexiones",
    "blocked": "Sesiones bloqueadas", "locks": "Locks",
    "log_used_pct": "Log usado %", "service_down": "Servicio caído",
    "instance_unreachable": "Instancia inalcanzable",
}

# Plantillas recomendadas (se seedean por conexión desde la UI).
RULE_TEMPLATES = [
    {"metric": "cpu_percent", "name": "CPU alta sostenida", "operator": "gt", "threshold": 85,
     "severity": "critical", "scope": "instance", "suggested_workaround_key": "kill_blocking_sessions",
     "description": "CPU del proceso SQL por encima del 85%."},
    {"metric": "memory_percent", "name": "Memoria alta", "operator": "gt", "threshold": 90,
     "severity": "warning", "scope": "instance", "suggested_workaround_key": "clear_plan_cache",
     "description": "Uso de memoria del servidor por encima del 90%."},
    {"metric": "blocked", "name": "Sesiones bloqueadas", "operator": "gt", "threshold": 0,
     "severity": "warning", "scope": "instance", "suggested_workaround_key": "kill_blocking_sessions",
     "auto_remediate": True, "auto_threshold": 5,
     "description": "Hay sesiones bloqueadas. Auto-remedia (KILL) si llegan a 5."},
    {"metric": "log_used_pct", "name": "Log de transacciones lleno", "operator": "gt", "threshold": 80,
     "severity": "warning", "scope": "database", "suggested_workaround_key": "shrink_log",
     "auto_remediate": True, "auto_threshold": 99,
     "description": "Log de la base por encima del 80%. Auto-shrink al 99%."},
    {"metric": "service_down", "name": "Servicio SQL caído", "operator": "gte", "threshold": 1,
     "severity": "critical", "scope": "availability", "suggested_workaround_key": "start_sql_service",
     "auto_remediate": True, "auto_threshold": 1,
     "description": "El servicio de SQL Server no está corriendo. Auto-inicia (WinRM)."},
    {"metric": "instance_unreachable", "name": "Instancia inalcanzable", "operator": "gte", "threshold": 1,
     "severity": "critical", "scope": "availability", "suggested_workaround_key": "start_sql_service",
     "description": "No se puede conectar a la instancia."},
]

_LOG_USED_SQL = (
    "SELECT CAST(100.0 * SUM(CAST(FILEPROPERTY(name,'SpaceUsed') AS BIGINT)) "
    "/ NULLIF(SUM(CAST(size AS BIGINT)), 0) AS DECIMAL(5,2)) "
    "FROM sys.database_files WHERE type = 1"
)


def templates() -> list[dict]:
    return [dict(t) for t in RULE_TEMPLATES]


def _conn_ctx(connection_id: str, cache: dict) -> dict:
    """Métricas de instancia (una sola vez por conexión) + flag de inalcanzable."""
    if connection_id in cache:
        return cache[connection_id]
    ctx = {"metrics": {}, "unreachable": False}
    try:
        eng = connections_repo.get_engine(connection_id)
        if eng is None:
            ctx["unreachable"] = True
        else:
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            ctx["metrics"] = performance_repo.get_metrics(eng)
    except Exception:  # noqa: BLE001
        ctx["unreachable"] = True
    cache[connection_id] = ctx
    return ctx


def _metric_value(metric: str, connection_id: str, database: str, cache: dict) -> float | None:
    """Valor actual de la métrica. None si no se pudo leer (no rompe la evaluación)."""
    ctx = _conn_ctx(connection_id, cache)
    if metric == "instance_unreachable":
        return 1.0 if ctx["unreachable"] else 0.0
    if metric == "service_down":
        cfg = connections_repo.host_control_config(connection_id)
        if cfg is None:
            return None
        st = host_control.service_status(cfg)
        return 0.0 if st["status"] == "Running" else 1.0
    if ctx["unreachable"]:
        return None
    if metric == "log_used_pct":
        eng = connections_repo.get_engine_for_db(connection_id, database)
        if eng is None:
            return None
        with eng.connect() as conn:
            val = conn.execute(text(_LOG_USED_SQL)).scalar()
        return float(val) if val is not None else None
    val = ctx["metrics"].get(metric)
    return float(val) if val is not None else None


def _in_cooldown(raw: dict) -> bool:
    last = raw.get("last_triggered")
    if not last:
        return False
    return (datetime.now(timezone.utc) - last).total_seconds() < raw.get("cooldown_seconds", 300)


def _title(metric: str, operator: str, threshold) -> str:
    return f"{_LABEL.get(metric, metric)} {_OP_SYM.get(operator, operator)} {threshold}"


def evaluate(actor: str = "scheduler") -> list[dict]:
    """Evalúa todas las reglas habilitadas una vez. Levanta/actualiza/resuelve alertas
    y auto-remedia donde corresponda. Tolerante a fallos por regla."""
    names = {c["id"]: c["name"] for c in connections_repo.list_all()}
    cache: dict = {}
    results: list[dict] = []

    for raw in alerts_repo.list_enabled_rules_raw():
        rule_id = str(raw["_id"])
        metric = raw.get("metric")
        conn, db = raw.get("connection_id", ""), raw.get("database", "")
        op = _OPS.get(raw.get("operator", "gt"), _OPS["gt"])
        threshold = raw.get("threshold")
        base = {"rule_id": rule_id, "name": raw.get("name", ""), "metric": metric}

        try:
            value = _metric_value(metric, conn, db, cache)
            if value is None:
                alerts_repo.mark_checked(rule_id, None, False)
                results.append({**base, "checked": False, "breached": False,
                                "status": "métrica no disponible"})
                continue

            breached = op(value, threshold)
            auto = False
            if breached:
                source = names.get(conn, conn) + (f"/{db}" if db else "")
                alert = alerts_repo.raise_or_update({
                    "rule_id": rule_id, "connection_id": conn, "source": source,
                    "metric": metric, "value": value, "threshold": threshold,
                    "severity": raw.get("severity", "warning"),
                    "title": _title(metric, raw.get("operator", "gt"), threshold),
                    "description": f"Valor actual {value} (umbral {threshold}).",
                    "suggested_workaround_key": raw.get("suggested_workaround_key"),
                })
                wk_key = raw.get("suggested_workaround_key")
                auto_thr = raw.get("auto_threshold")
                if (raw.get("auto_remediate") and wk_key and auto_thr is not None
                        and op(value, auto_thr) and not _in_cooldown(raw)):
                    wk = workaround_exec.resolve(wk_key)
                    if wk is not None:
                        workaround_exec.apply(wk, conn, db)
                        alerts_repo.mark_auto_remediated(alert["id"])
                        workarounds_repo.log_run(actor, wk_key, conn, db, "auto", success=True)
                        audit_repo.log(actor, "alert.auto_remediate", target=f"{conn}/{db}",
                                       detail=f"{wk_key} · {metric}={value}")
                        auto = True
            else:
                alerts_repo.resolve_active_for_rule(rule_id)

            alerts_repo.mark_checked(rule_id, value, auto)
            results.append({**base, "checked": True, "breached": breached,
                            "value": value, "auto_remediated": auto})
        except Exception as exc:  # noqa: BLE001
            results.append({**base, "checked": False, "breached": False, "error": str(exc)})
    return results
