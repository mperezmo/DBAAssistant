# backend/app/models/connection.py
"""Modelos de conexiones a INSTANCIAS de SQL Server (Sprint 4).

Una conexión apunta a una instancia (host/puerto/credenciales), no a una base
puntual. La base a analizar se elige aparte (en Esquema de BD).
"""
from pydantic import BaseModel


class ConnectionCreate(BaseModel):
    name: str
    host: str
    port: int = 1433
    username: str
    password: str


class Connection(BaseModel):
    """Salida pública: NUNCA incluye la contraseña."""
    id: str
    name: str
    host: str
    port: int
    username: str


class ConnectionTestResult(BaseModel):
    ok: bool
    server: str | None = None
    detail: str | None = None
