# backend/app/services/scheduler.py
"""Scheduler interno de automatización (Sprint 10.1).

Hilo daemon, sin dependencias externas: si ``automation_enabled`` está activo,
evalúa las reglas cada ``automation_interval_seconds``. Opt-in por env y apagado
por defecto (auto-remediar es sensible). Con varios workers de uvicorn habría un
scheduler por worker → para evaluación periódica usar 1 worker o un cron externo
contra ``POST /workarounds/rules/evaluate``.
"""
import threading
import time

from app.config import get_settings

_started = False
_lock = threading.Lock()


def _loop(interval: int) -> None:
    from app.services import automation  # import diferido: evita ciclos al cargar la app

    while True:
        time.sleep(interval)
        try:
            automation.evaluate_rules("scheduler")
        except Exception:  # noqa: BLE001  — el scheduler nunca debe morir por un error
            pass


def start() -> bool:
    """Arranca el scheduler si está habilitado. Idempotente. Devuelve si quedó activo."""
    global _started
    settings = get_settings()
    if not settings.automation_enabled:
        return False
    with _lock:
        if _started:
            return True
        interval = max(10, settings.automation_interval_seconds)
        threading.Thread(target=_loop, args=(interval,), daemon=True,
                         name="workaround-automation").start()
        _started = True
    return True
