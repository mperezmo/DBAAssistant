# backend/app/services/workaround_exec.py
"""Ejecución reutilizable de workarounds (Sprint 11).

Helpers compartidos por la ejecución manual (routes/workarounds) y por la
auto-remediación dirigida por Alertas (services/alerts):
- ``diagnose_count`` corre el diagnóstico y devuelve cuántos "problemas" hay.
- ``apply`` ejecuta la remediación (SQL o servicio Windows vía WinRM).

(Antes vivía en services/automation.py, junto al motor de reglas de workaround
que se reemplazó por el motor de Alertas.)
"""
from app.services import connections_repo, host_control, sql_executor, workarounds, workarounds_repo


def resolve(key: str) -> dict | None:
    """Busca un workaround por key: primero built-in, luego custom."""
    return workarounds.get_builtin(key) or workarounds_repo.get_custom(key)


def diagnose_count(wk: dict, connection_id: str, database: str) -> tuple[int, str]:
    """Cantidad de 'problemas' detectados por el diagnóstico + un texto de estado."""
    if wk.get("kind") == "service":
        cfg = connections_repo.host_control_config(connection_id)
        if cfg is None:
            raise RuntimeError("Control de host (WinRM) no configurado para esta conexión.")
        st = host_control.service_status(cfg)
        down = st["status"] != "Running"
        return (1 if down else 0, f"{st['service_name']}: {st['status']}")
    engine = connections_repo.get_engine_for_db(connection_id, database)
    if engine is None:
        raise RuntimeError("Conexión o base de datos no encontrada.")
    _cols, rows, _trunc = sql_executor.run_select(engine, wk["diagnose_sql"])
    return (len(rows), f"{len(rows)} fila(s) de diagnóstico")


def apply(wk: dict, connection_id: str, database: str) -> str:
    """Ejecuta la remediación y devuelve un texto de resultado."""
    if wk.get("kind") == "service":
        cfg = connections_repo.host_control_config(connection_id)
        if cfg is None:
            raise RuntimeError("Control de host (WinRM) no configurado para esta conexión.")
        st = host_control.start_service(cfg)
        return f"{st['service_name']}: {st['status']}"
    engine = connections_repo.get_engine_for_db(connection_id, database)
    if engine is None:
        raise RuntimeError("Conexión o base de datos no encontrada.")
    out = sql_executor.run_script(engine, wk["apply_sql"])
    return f"{out['affected_rows']} filas afectadas" if out["affected_rows"] is not None else "aplicado"
