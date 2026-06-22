# backend/app/services/automation.py
"""Motor de automatización de Workarounds (Sprint 10.1).

Evalúa reglas "SI Y SOLO SI": corre el **diagnóstico** del workaround y, si detecta
el problema (≥ ``min_rows`` filas), ejecuta la **remediación**. Reutiliza el mismo
diagnóstico/aplicación que la ejecución manual:
- ``kind == "sql"``  → ``sql_executor.run_select`` / ``run_script`` por conexión+base.
- ``kind == "service"`` → ``host_control.service_status`` / ``start_service`` (WinRM).

Cada disparo se audita (``workaround.auto``) y respeta un cooldown por regla.
"""
from datetime import datetime, timezone

from app.services import (
    audit_repo, connections_repo, host_control, sql_executor, workarounds, workarounds_repo,
)


def _resolve(key: str) -> dict | None:
    return workarounds.get_builtin(key) or workarounds_repo.get_custom(key)


def _diagnose_count(wk: dict, connection_id: str, database: str) -> tuple[int, str]:
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


def _apply(wk: dict, connection_id: str, database: str) -> str:
    """Ejecuta la remediación y devuelve un texto de resultado."""
    if wk.get("kind") == "service":
        cfg = connections_repo.host_control_config(connection_id)
        st = host_control.start_service(cfg)
        return f"{st['service_name']}: {st['status']}"
    engine = connections_repo.get_engine_for_db(connection_id, database)
    out = sql_executor.run_script(engine, wk["apply_sql"])
    return f"{out['affected_rows']} filas afectadas" if out["affected_rows"] is not None else "aplicado"


def _in_cooldown(raw: dict) -> bool:
    last = raw.get("last_triggered")
    if not last:
        return False
    elapsed = (datetime.now(timezone.utc) - last).total_seconds()
    return elapsed < raw.get("cooldown_seconds", 300)


def evaluate_rules(actor: str = "scheduler") -> list[dict]:
    """Evalúa TODAS las reglas habilitadas una vez. Devuelve un resumen por regla.

    Tolerante a fallos: un error en una regla no frena a las demás.
    """
    results: list[dict] = []
    for raw in workarounds_repo.list_enabled_rules_raw():
        rule_id = str(raw["_id"])
        key = raw.get("workaround_key", "")
        conn, db = raw.get("connection_id", ""), raw.get("database", "")
        base = {"rule_id": rule_id, "name": raw.get("name", ""), "workaround_key": key}

        wk = _resolve(key)
        if wk is None:
            results.append({**base, "checked": False, "triggered": False,
                            "error": "Workaround inexistente."})
            continue
        if _in_cooldown(raw):
            results.append({**base, "checked": False, "triggered": False, "status": "en cooldown"})
            continue

        try:
            problems, status_text = _diagnose_count(wk, conn, db)
            if problems >= raw.get("min_rows", 1):
                apply_status = _apply(wk, conn, db)
                workarounds_repo.log_run(actor, key, conn, db, "auto", success=True)
                audit_repo.log(actor, "workaround.auto", target=f"{conn}/{db}",
                               detail=f"{key} · applied · {apply_status}")
                workarounds_repo.mark_checked(rule_id, triggered=True, status=apply_status)
                results.append({**base, "checked": True, "triggered": True,
                                "problems": problems, "status": apply_status})
            else:
                workarounds_repo.mark_checked(rule_id, triggered=False, status=status_text)
                results.append({**base, "checked": True, "triggered": False,
                                "problems": problems, "status": status_text})
        except Exception as exc:  # noqa: BLE001
            workarounds_repo.log_run(actor, key, conn, db, "auto", success=False, error=str(exc))
            workarounds_repo.mark_checked(rule_id, triggered=False, status=f"error: {exc}")
            results.append({**base, "checked": True, "triggered": False, "error": str(exc)})
    return results
