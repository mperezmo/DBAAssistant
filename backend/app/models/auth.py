# backend/app/models/auth.py
"""Modelos Pydantic para autenticación."""
from pydantic import BaseModel


class Token(BaseModel):
    """Respuesta del endpoint de login."""
    access_token: str
    token_type: str = "bearer"


class User(BaseModel):
    """Usuario público (sin datos sensibles)."""
    username: str
    full_name: str | None = None
    email: str | None = None
    roles: list[str] = []


class UserInDB(User):
    """Usuario tal como se almacena (incluye el hash de la contraseña)."""
    hashed_password: str
