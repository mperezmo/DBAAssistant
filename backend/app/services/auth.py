# backend/app/services/auth.py
"""Lógica de autenticación: hashing de contraseñas y manejo de JWT.

Soporta dos modos (config.auth_mode):
  - "local": emite y valida JWT propios firmados con HS256 (SECRET_KEY).
  - "auth0": valida JWT RS256 emitidos por Auth0 contra su JWKS público.
"""
from datetime import datetime, timedelta, timezone

import jwt
from jwt import PyJWKClient
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Contraseñas ───────────────────────────────────────────────
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT local (HS256) ─────────────────────────────────────────
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Crea un JWT firmado localmente. Usado solo en auth_mode='local'."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


# ── JWT Auth0 (RS256 + JWKS) ──────────────────────────────────
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    """Cliente JWKS perezoso que cachea las claves públicas de Auth0."""
    global _jwks_client
    if _jwks_client is None:
        url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
        _jwks_client = PyJWKClient(url)
    return _jwks_client


def decode_token(token: str) -> dict:
    """Decodifica y valida un token según el modo configurado.

    Lanza excepciones de PyJWT (InvalidTokenError, ExpiredSignatureError, ...)
    si el token no es válido; el caller debe capturarlas.
    """
    if settings.auth_mode == "auth0":
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )
    # modo local
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
