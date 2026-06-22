# backend/app/services/scheduler.py
"""Scheduler interno de Alertas (Sprint 11; antes era de Workarounds, 10.1).

Hilo daemon, sin dependencias externas: si ``alerts_enabled`` está activo, evalúa
las reglas de alerta cada ``alerts_interval_seconds`` (chequea métricas, levanta
alertas y auto-remedia al umbral máximo). Opt-in por env y apagado por defecto.
Con varios workers de uvicorn habría un scheduler por worker → para evaluación
periódica usar 1 worker o un cron externo contra ``POST /alerts/evaluate``.
"""
import threading
import time

from app.config import get_settings

_started = False
_lock = threading.Lock()


def _loop(interval: int) -> None:
    from app.services import alerts  # import diferido: evita ciclos al cargar la app

    while True:
        time.sleep(interval)
        try:
            alerts.evaluate("scheduler")
        except Exception:  # noqa: BLE001  — el scheduler nunca debe morir por un error
            pass


def start() -> bool:
    """Arranca el scheduler si está habilitado. Idempotente. Devuelve si quedó activo."""
    global _started
    settings = get_settings()
    if not settings.alerts_enabled:
        return False
    with _lock:
        if _started:
            return True
        interval = max(10, settings.alerts_interval_seconds)
        threading.Thread(target=_loop, args=(interval,), daemon=True,
                         name="alerts-scheduler").start()
        _started = True
    return True
