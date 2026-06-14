# backend/app/routes/auth.py
"""Rutas de autenticación: login (modo local) y perfil del usuario."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.config import get_settings
from app.dependencies import get_current_user
from app.models.auth import Token, User
from app.services import auth, users

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login con usuario/contraseña → devuelve un JWT (solo modo local).

    En modo 'auth0' el login lo gestiona el frontend con el SDK de Auth0,
    así que este endpoint queda deshabilitado.
    """
    if settings.auth_mode != "local":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login local deshabilitado (AUTH_MODE=auth0). Usa el flujo de Auth0.",
        )
    user = users.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(
        data={"sub": user.username, "roles": user.roles}
    )
    return Token(access_token=access_token)


@router.get("/me", response_model=User)
def read_me(current_user: User = Depends(get_current_user)):
    """Ruta PROTEGIDA: devuelve el usuario autenticado. Requiere Bearer token."""
    return current_user
