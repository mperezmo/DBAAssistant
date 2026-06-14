# backend/app/dependencies.py
"""Dependencias de FastAPI para proteger rutas."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import get_settings
from app.models.auth import User
from app.services import auth, users

settings = get_settings()

# tokenUrl es la ruta donde el cliente obtiene el token (para la doc de Swagger)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

_credentials_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudieron validar las credenciales",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Valida el JWT (Bearer) y devuelve el usuario autenticado.

    Funciona en ambos modos:
      - local: el 'sub' del token referencia un usuario del almacén local.
      - auth0: el usuario se construye a partir de los claims del token.
    """
    try:
        payload = auth.decode_token(token)
    except Exception:
        raise _credentials_exc

    username: str | None = payload.get("sub")
    if not username:
        raise _credentials_exc

    if settings.auth_mode == "auth0":
        # Auth0 entrega los datos en los claims del propio token.
        return User(
            username=username,
            email=payload.get("email"),
            roles=payload.get("permissions", []) or [],
        )

    # Modo local: buscamos el usuario en el almacén.
    user = users.get_user(username)
    if not user:
        raise _credentials_exc
    return User(**user.model_dump(exclude={"hashed_password"}))
