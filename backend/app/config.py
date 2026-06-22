# backend/app/config.py
from functools import lru_cache
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DBA Assistant"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"
    # Prefijo cuando corre detrás de un reverse proxy (ej. "/api" en producción)
    root_path: str = ""

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

    # ── Claude / IA (Sprint 3) ────────────────────────────────
    anthropic_api_key: str = ""
    claude_model: str = "claude-3-5-sonnet-20241022"
    claude_max_tokens: int = 1024

    # ── Alertas (Sprint 11) ───────────────────────────────────
    # Scheduler interno: evalúa las reglas de alerta cada N segundos (chequea
    # métricas, levanta alertas y auto-remedia al umbral máximo). Apagado por
    # defecto (la auto-remediación es sensible); activar con ALERTS_ENABLED=true.
    alerts_enabled: bool = False
    alerts_interval_seconds: int = 60

    # ── Conexión "target" para análisis (Sprint 4) ────────────
    # SQL Server externo a analizar (p. ej. tu instancia local). Si
    # target_sql_host está vacío, el análisis usa la conexión principal.
    target_sql_host: str = ""
    target_sql_port: int = 1433
    target_sql_user: str = ""
    target_sql_password: str = ""
    target_sql_database: str = ""

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @staticmethod
    def _odbc_url(user: str, password: str, host: str, port: int, database: str) -> str:
        driver = "ODBC+Driver+18+for+SQL+Server"
        u, p, d = quote(str(user), safe=""), quote(str(password), safe=""), quote(str(database), safe="")
        return (
            f"mssql+pyodbc://{u}:{p}@{host}:{port}/{d}"
            f"?driver={driver}&TrustServerCertificate=yes"
        )

    @property
    def sqlserver_url(self) -> str:
        return self._odbc_url(
            self.sql_server_user, self.sql_server_password,
            self.sql_server_host, self.sql_server_port, self.sql_server_database,
        )

    @property
    def has_target(self) -> bool:
        return bool(self.target_sql_host)

    @property
    def target_sqlserver_url(self) -> str:
        """URL del SQL Server a analizar. Si no hay target, usa el principal."""
        if not self.has_target:
            return self.sqlserver_url
        return self._odbc_url(
            self.target_sql_user, self.target_sql_password,
            self.target_sql_host, self.target_sql_port, self.target_sql_database,
        )


@lru_cache
def get_settings() -> Settings:
    # Producción opcional: hidrata el entorno desde Azure Key Vault si está
    # configurado (AZURE_VAULT_URL). No-op en desarrollo.
    from app.keyvault import load_secrets

    load_secrets()
    return Settings()