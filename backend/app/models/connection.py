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


class HostControl(BaseModel):
    """Config WinRM para controlar el servicio Windows (Sprint 10.1). Sin password."""
    win_host: str = ""           # vacío → usa el host de la conexión
    service_name: str = ""       # ej. MSSQLSERVER o MSSQL$INSTANCIA
    username: str = ""
    port: int = 5985
    transport: str = "ntlm"
    has_password: bool = False


class HostControlIn(BaseModel):
    """Alta/edición de la config WinRM (incluye password; '' conserva el guardado)."""
    win_host: str = ""
    service_name: str = ""
    username: str = ""
    password: str = ""
    port: int = 5985
    transport: str = "ntlm"
