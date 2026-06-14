# backend/app/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DBA Assistant"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"

    sql_server_host: str
    sql_server_port: int = 1433
    sql_server_user: str
    sql_server_password: str
    sql_server_database: str

    mongodb_uri: str
    mongodb_database: str

    redis_url: str

    # ── Autenticación (Sprint 2) ──────────────────────────────
    # Modo de auth: "local" (JWT HS256 propio) o "auth0" (RS256 + JWKS)
    auth_mode: str = "local"
    secret_key: str = "change-me-in-prod"          # firma HS256 en modo local
    access_token_expire_minutes: int = 60
    # Auth0 (se usan solo si auth_mode == "auth0")
    auth0_domain: str = ""
    auth0_client_id: str = ""
    auth0_client_secret: str = ""
    auth0_audience: str = ""

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlserver_url(self) -> str:
        driver = "ODBC+Driver+18+for+SQL+Server"
        return (
            f"mssql+pyodbc://{self.sql_server_user}:{self.sql_server_password}"
            f"@{self.sql_server_host}:{self.sql_server_port}/{self.sql_server_database}"
            f"?driver={driver}&TrustServerCertificate=yes"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()