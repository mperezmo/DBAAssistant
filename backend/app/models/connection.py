# backend/app/models/connection.py
"""Modelos de conexiones a SQL Server gestionadas por el usuario (Sprint 4)."""
from pydantic import BaseModel


class ConnectionCreate(BaseModel):
    name: str
    host: str
    port: int = 1433
    username: str
    password: str
    database: str


class Connection(BaseModel):
    """Salida pública: NUNCA incluye la contraseña."""
    id: str
    name: str
    host: str
    port: int
    username: str
    database: str


class ConnectionTestResult(BaseModel):
    ok: bool
    server: str | None = None
    detail: str | None = None
