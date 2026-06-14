# backend/app/services/users.py
"""Almacén de usuarios para el modo de auth LOCAL.

⚠️ Sprint 2: almacén en memoria con usuarios sembrados. No persiste entre
reinicios. En un sprint posterior debe reemplazarse por una tabla en SQL Server
(repositorio con SQLAlchemy) sin cambiar la interfaz pública de este módulo.
"""
from app.models.auth import UserInDB
from app.services.auth import get_password_hash, verify_password

# Usuarios de demo (modo local). Credenciales: admin/admin123, dba/dba12345
_USERS: dict[str, UserInDB] = {
    "admin": UserInDB(
        username="admin",
        full_name="Administrador",
        email="admin@dba.local",
        roles=["admin"],
        hashed_password=get_password_hash("admin123"),
    ),
    "dba": UserInDB(
        username="dba",
        full_name="DBA User",
        email="dba@dba.local",
        roles=["dba"],
        hashed_password=get_password_hash("dba12345"),
    ),
}


def get_user(username: str) -> UserInDB | None:
    return _USERS.get(username)


def authenticate_user(username: str, password: str) -> UserInDB | None:
    """Devuelve el usuario si las credenciales son válidas, si no None."""
    user = get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
