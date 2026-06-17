# Despliegue (Producción) — DBA Assistant

Estructura lista para producción. Lo que falta es **completar credenciales**
(igual que con la API de Claude). Esta guía dice **qué** cargar y **dónde**.

## Arquitectura objetivo (Azure)

```
Internet ──▶ Reverse proxy (nginx)
                 ├── /        → Frontend (React/Vite, estático)
                 └── /api/    → Backend (FastAPI)  ──▶ Azure SQL
                                                    ──▶ Cosmos DB (MongoDB API)
                                                    ──▶ Azure Cache for Redis
                                                    ──▶ Anthropic Claude API
                                                    ──▶ Auth0 (JWKS)
   Secretos: Azure Key Vault   ·   Imágenes: GHCR/ACR   ·   CI/CD: GitHub Actions
```

## Pipelines (GitHub Actions)

| Workflow | Disparo | Qué hace | Requiere |
|----------|---------|----------|----------|
| `ci.yml` | push / PR a `main` | tests + build frontend + build imágenes | nada |
| `release.yml` | tag `vX.Y.Z` | **publica** imágenes backend/frontend a **GHCR** | nada (usa `GITHUB_TOKEN`) |
| `deploy-azure.yml` | manual | **despliega** a Azure Container Apps | secretos/vars de Azure |

### Variables/Secretos a configurar en GitHub
`Settings → Secrets and variables → Actions`

**Variables** (públicas, para compilar el frontend en `release.yml`):
- `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`, `VITE_AUTH0_AUDIENCE`
- `AZURE_RESOURCE_GROUP`, `AZURE_BACKEND_APP`, `AZURE_FRONTEND_APP`

**Secrets**:
- `AZURE_CREDENTIALS` — JSON del service principal:
  ```bash
  az ad sp create-for-rbac --name dba-assistant --role contributor \
    --scopes /subscriptions/<SUB_ID>/resourceGroups/<RG> --sdk-auth
  ```

## Configuración del backend (`.env.production`)

1. `cp .env.production.example .env.production` y completar.
2. `SECRET_KEY`: `python -c "import secrets;print(secrets.token_urlsafe(48))"`.
3. Apuntar las bases a servicios gestionados (Azure SQL / Cosmos Mongo / Azure Cache for Redis).
4. `AUTH_MODE=auth0` + datos del tenant/app de producción.
5. `ANTHROPIC_API_KEY` para el chat y la generación de SQL.

### Secretos vía Azure Key Vault (opcional, recomendado en prod)
- Crear un Key Vault y cargar los secretos con **guiones**: `SQL-SERVER-PASSWORD`,
  `ANTHROPIC-API-KEY`, `SECRET-KEY`, etc.
- En el backend: `pip install -r backend/requirements-azure.txt` y setear
  `AZURE_VAULT_URL=https://<tu-vault>.vault.azure.net/`.
- Al arrancar, `app/keyvault.py` hidrata el entorno desde el Vault (los nombres
  con guiones se mapean a variables con guion bajo). Sin `AZURE_VAULT_URL`, es no-op.

## Probar el stack de producción localmente

```bash
cp .env.production.example .env.production   # completar valores
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
# Único puerto público: http://localhost  (proxy → / frontend, /api backend)
```

Diferencias clave del modo prod:
- Backend con **múltiples workers** (sin `--reload`).
- **Reverse proxy nginx** como única entrada; las bases no exponen puertos.
- Frontend compilado con `VITE_API_BASE_URL=/api` (mismo origen, vía proxy).
- Backend con `ROOT_PATH=/api` (para que `/api/docs` funcione tras el proxy).

## Checklist de salida a producción
- [ ] Recursos Azure creados (RG, Container Apps, ACR o GHCR, Key Vault, Azure SQL/Cosmos/Redis).
- [ ] Auth0: app SPA con callbacks/origins del **dominio de producción**.
- [ ] Secrets/Variables cargados en GitHub Actions.
- [ ] `.env.production` o Key Vault completos.
- [ ] Tag `vX.Y.Z` → `release.yml` publica imágenes.
- [ ] `deploy-azure.yml` (manual) despliega esas imágenes.
- [ ] TLS/HTTPS en el proxy (certificado) y `CORS_ORIGINS` al dominio real.
