# backend/app/services/sql_validator.py
"""Validación/analísis ligero de seguridad de SQL (Sprint 5)."""
import re


def is_read_only(sql: str) -> bool:
    """True si la sentencia es de solo lectura (SELECT / CTE)."""
    s = sql.strip().lstrip("(").strip().lower()
    return s.startswith("select") or s.startswith("with")


def analyze(sql: str) -> list[str]:
    """Devuelve advertencias para operaciones riesgosas (heurístico)."""
    low = sql.lower()
    warnings: list[str] = []
    if re.search(r"\b(drop|truncate)\b", low):
        warnings.append("Operación destructiva detectada (DROP/TRUNCATE).")
    if re.search(r"\bdelete\b", low) and not re.search(r"\bwhere\b", low):
        warnings.append("DELETE sin WHERE: afectaría TODAS las filas.")
    if re.search(r"\bupdate\b", low) and not re.search(r"\bwhere\b", low):
        warnings.append("UPDATE sin WHERE: afectaría TODAS las filas.")
    return warnings
