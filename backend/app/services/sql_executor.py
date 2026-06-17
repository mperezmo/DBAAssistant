# backend/app/services/sql_executor.py
"""Ejecución CONTROLADA de SQL (Sprint 5).

- SELECT/CTE: solo lectura, devuelve filas (máx 1000).
- Escritura/DDL:
    - mode="preview": ejecuta dentro de una transacción y hace ROLLBACK
      (te dice cuántas filas afectaría, sin aplicar nada).
    - mode="apply": ejecuta dentro de una transacción y hace COMMIT.
"""
import time

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.services.sql_validator import is_read_only

_MAX_ROWS = 1000


def _safe(value):
    if value is None or isinstance(value, (int, float, bool, str)):
        return value
    return str(value)


def _ms(start: float) -> int:
    return int((time.time() - start) * 1000)


def run(engine: Engine, sql: str, mode: str) -> dict:
    start = time.time()

    if is_read_only(sql):
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [[_safe(v) for v in row] for row in result.fetchmany(_MAX_ROWS)]
        return {"kind": "select", "columns": columns, "rows": rows,
                "affected_rows": None, "committed": False, "elapsed_ms": _ms(start)}

    if mode == "apply":
        with engine.begin() as conn:  # COMMIT al salir sin error
            affected = conn.execute(text(sql)).rowcount
        committed = True
    else:  # preview → ROLLBACK
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                affected = conn.execute(text(sql)).rowcount
            finally:
                trans.rollback()
        committed = False

    affected = None if affected is None or affected < 0 else int(affected)
    return {"kind": "write", "columns": None, "rows": None,
            "affected_rows": affected, "committed": committed, "elapsed_ms": _ms(start)}
