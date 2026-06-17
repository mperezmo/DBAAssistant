# backend/app/keyvault.py
"""Carga opcional de secretos desde Azure Key Vault (producción · Sprint 7).

Igual que la integración de Claude: si NO está configurado, es un no-op total.
Si `AZURE_VAULT_URL` está definido y las libs de Azure están instaladas
(backend/requirements-azure.txt), trae los secretos del Vault y los inyecta en
el entorno para que `Settings` los tome.

Convención: los nombres de secreto en el Vault usan guiones (no admite '_'),
ej. `SQL-SERVER-PASSWORD` → se mapea a la variable de entorno `SQL_SERVER_PASSWORD`.
Las variables ya presentes en el entorno NO se sobreescriben.
"""
import os


def load_secrets() -> None:
    vault_url = os.environ.get("AZURE_VAULT_URL")
    if not vault_url:
        return  # no configurado → no-op (como sin Claude)

    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
    except Exception:
        # libs de Azure no instaladas (requirements-azure.txt) → seguir con env vars
        return

    try:
        client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
        for prop in client.list_properties_of_secrets():
            env_name = prop.name.replace("-", "_").upper()
            if env_name not in os.environ:
                os.environ[env_name] = client.get_secret(prop.name).value
    except Exception:
        # Si el Vault no responde, no romper el arranque: se usa el entorno tal cual.
        return
