# DBA Assistant - Project Context

> Documento vivo de contexto del proyecto. Sirve como referencia para retomar el
> trabajo en cualquier momento (humano o asistente IA).
>
> **Última actualización:** 2026-06-14
> **Estado actual:** Sprints 1-8 ✅ — proyecto completo (último tag v0.7.0).
> Deploy real a Azure pendiente solo de credenciales del usuario.
>
> **Cambio de arquitectura (Sprint 3):** el frontend pasó de HTML/JS vanilla a
> **React + Vite** (proyecto en `frontend/`, build multi-stage en Docker → nginx).
> Se implementó el diseño de Claude Design (`design/DBA Assistant.html`): login
> (Auth0), shell (sidebar + topbar) y páginas conectadas al backend. Login = **Auth0**.
>
> **Auth0 (funcionando):** app SPA `DBAAssistant`, API/audience `https://dba-assistant-api`.
> Login OK tras: (1) crear la API en Auth0, (2) habilitar **User-Delegated Access**
> en esa API. El `AUTH0_CLIENT_ID` se incrusta en el build del frontend (build arg).
>
> **Sprint 4 (en curso):** introspección real de SQL Server (tablas, columnas,
> índices, FKs) y **gestor de conexiones dinámico**:
> - **Panel Admin** (`/connections` CRUD): el usuario agrega/borra conexiones a
>   **instancias** SQL Server (alias/host/puerto/usuario/password — SIN base; se
>   conecta a `master`). Se guardan en MongoDB. No hay nada por defecto.
> - **Descubrimiento de bases** (`/connections/{id}/databases`): lista las bases
>   no-sistema y no-ReportServer (online) de la instancia.
> - **Esquema de BD por instancia + base** (`/schema/{connection_id}/{database}/*`):
>   en "Esquema de BD" se elige instancia y luego base; `connections_repo` cachea
>   un engine por (conexión, base) y valida que la base sea una de las permitidas.
> - **Monitoreo** es a nivel **instancia** (DMVs de servidor): el selector lista
>   instancias, no bases (evita redundancia).
> - Frontend: páginas `Admin.jsx` (servicios + alta/baja/test de conexiones) y
>   `Schema.jsx` (selector de conexión + overview/tablas/detalle). Conexión activa
>   en `localStorage`.
> - ⚠️ Las contraseñas se guardan en Mongo en texto plano (dev/TFI). En prod:
>   cifrar / Azure Key Vault. La API nunca devuelve la contraseña.
> - **Puertos:** el SQL propio del app se publica en el host en **14330** (no 1433)
>   para dejar el **1433 libre** a las instancias que el usuario agregue a
>   monitorear. El backend usa el SQL del app por red interna (`sqlserver:1433`),
>   no por el puerto publicado. Para SSMS contra el SQL del app: `localhost,14330`.
> - Para apuntar a la instancia local del usuario: host `host.docker.internal`,
>   con TCP + login SQL habilitados y el puerto donde escuche (1433 si es default).
> - `TARGET_SQL_*` en `.env` quedó como **legacy** (ya no se usa).
> - `backend/scripts/seed_schema.sql`: esquema de ejemplo (para la BD `DBAAssistant`).
> - **Análisis de performance** (`/performance/{connection_id}/*`): métricas vía DMVs
>   (CPU% ring buffer, memoria %, sesiones, conexiones, bloqueos, locks), sesiones
>   activas (`dm_exec_requests`) y top queries por CPU (`dm_exec_query_stats`).
>   Página "Monitoreo" (gauges + counters + tablas, auto-refresh 10s) con
>   **detección básica de anomalías** (resalta bloqueadas / CPU alta / long-running).
>   Requiere que el login de la conexión tenga **VIEW SERVER STATE**.
> - **Auditoría** (`/audit`): bitácora en MongoDB (colección `audit_log`) con
>   quién/qué/cuándo/IP. Se registran `connection.create`, `connection.delete` y
>   `schema.view`. Página "Auditoría" con tabla filtrable. `audit_repo.log()` es
>   tolerante a fallos (auditar nunca rompe la acción). Diseñado para extenderse
>   en Sprint 5 (p. ej. `query.execute`).
>
> **Sprint 5 (en curso) — generación y ejecución de SQL (página Sandbox):**
> - `POST /sql/generate`: NL→T-SQL con Claude (usa los nombres de tablas de la
>   base como contexto). Requiere ANTHROPIC_API_KEY.
> - `POST /sql/execute`: ejecución CONTROLADA. SELECT solo lectura (máx 1000 filas).
>   Escrituras/DDL: `mode=preview` (transacción + ROLLBACK, informa filas afectadas)
>   o `mode=apply` (transacción + COMMIT). Validación heurística (DELETE/UPDATE sin
>   WHERE, DROP/TRUNCATE) → warnings.
> - `GET /sql/history`: historial en MongoDB (`query_history`). Cada ejecución se
>   audita como `query.execute`. Servicios: `sql_validator`, `sql_executor`,
>   `query_history_repo`.
>
> **Sprint 6 (en curso) — caché Redis (`services/cache.py`):**
> - Cachea metadata (`/connections/{id}/databases`, `/schema/.../overview|tables|
>   tables/{s}/{t}`) con TTL 5 min. `?refresh=true` saltea y repuebla.
> - Invalidación por conexión: al borrar una conexión y tras una escritura
>   aplicada (`/sql/execute` con commit).
> - Stats hit/miss/ratio/keys (`GET /cache/stats`) + `POST /cache/clear`. Panel
>   "Caché · Redis" en el Panel Admin.
> - **Circuit breaker**: si Redis falla, no se reintenta por 10s (degrada a
>   cache-miss sin pagar timeouts). Todo tolerante a fallos.
> - **Query optimization** (`/optimization/{conn}/{db}/{missing,unused}-indexes`):
>   índices faltantes (`sys.dm_db_missing_index_*`) con CREATE sugerido, e índices
>   sin uso (`sys.dm_db_index_usage_stats`) con DROP sugerido. Página "Optimización"
>   (Operaciones) con copiar al portapapeles. Requiere VIEW SERVER STATE.
>
> **Sprint 7 — DevOps & estructura de producción (lista para configurar):**
> - CI `.github/workflows/ci.yml` (push/PR a main): pytest + build frontend + build
>   de imágenes. **Pasa en verde.**
> - CD `.github/workflows/release.yml` (tags `v*`): publica imágenes backend/frontend
>   a **GHCR** (usa `GITHUB_TOKEN`, sin secretos externos).
> - `deploy-azure.yml` (manual `workflow_dispatch`): **scaffold** de deploy a Azure
>   Container Apps; corre cuando cargás `AZURE_CREDENTIALS` + variables y lo disparás.
> - Producción self-host: `docker-compose.prod.yml` (workers, sin reload, bases sin
>   puertos) + **reverse proxy** `nginx/nginx.conf` (`/`→front, `/api/`→backend).
>   Backend soporta `ROOT_PATH=/api`.
> - Secretos: `.env.production.example` con todos los placeholders +
>   **Azure Key Vault** opcional (`app/keyvault.py`, no-op sin `AZURE_VAULT_URL`;
>   deps en `backend/requirements-azure.txt`).
> - Guía completa de qué configurar: **`docs/DEPLOYMENT.md`**.
> - Pendiente del usuario (configurar): credenciales Azure, secrets/vars de GitHub,
>   `.env.production` o Key Vault, recursos gestionados (Azure SQL/Cosmos/Redis).
>
> **Sprint 8 — Testing & Docs:**
> - **Unit tests** (`tests/unit/`): 53 tests + **cobertura** (`pytest-cov`, ~67%).
>   `pytest.ini`: `testpaths=tests/unit` (el CI corre solo unit), `addopts=--cov=app`.
> - **Integration tests** (`tests/integration/`, marker `integration`): contra los
>   servicios reales (backend/Mongo/Redis por puertos publicados). Correr con
>   `python -m pytest tests/integration -v` con el stack levantado. Se saltean si
>   el servicio no está.
> - **API docs**: `/docs` (Swagger) y `/redoc` con descripción + tags por módulo
>   (`openapi_tags` en `main.py`). Resumen en `docs/API.md`.
> - **Docs**: `README.md`, `docs/USER_GUIDE.md`, `docs/API.md`, `docs/DEPLOYMENT.md`.

---

## 📋 Visión General
**Nombre:** DBA Assistant
**Tipo:** Aplicación Web Full-Stack
**Objetivo:** Asistente inteligente para administración y optimización de bases de
datos usando IA generativa (Claude API). Permite a DBAs interactuar en lenguaje
natural con sus bases de datos: generar SQL, analizar rendimiento y obtener
recomendaciones de optimización.

**Usuarios objetivo:** DBAs, desarrolladores, analistas de datos.
**Repositorio:** `C:\Users\marti\GitHub\DBAAssistant` (GitHub: mperezmo/DBAAssistant)

---

## 🚦 Estado de los Sprints

| Sprint | Tema | Estado |
|--------|------|--------|
| **1** | Fundamentos e Infraestructura | ✅ **COMPLETADO** |
| **2** | Autenticación y Seguridad (Auth0 + JWT) | ✅ **COMPLETADO** (modo local; Auth0 listo a falta de tenant) |
| 3 | Chat & Claude API | ⬜ Pendiente |
| **4** | Análisis de BD (metadata, performance, anomalías, auditoría) | ✅ **COMPLETADO** |
| **5** | Generación y Ejecución SQL | ✅ **COMPLETADO** (v0.5.0) |
| **6** | Cache & Optimización (Redis) | ✅ **COMPLETADO** (caché + stats + optimización de índices) |
| **7** | DevOps & Deployment (CI/CD, Azure) | ✅ **COMPLETADO** (CI + CD a GHCR; deploy Azure = scaffold listo) |
| **8** | Testing & Docs | ✅ **COMPLETADO** |

---

## ✅ Sprint 1 — Lo que está HECHO y FUNCIONANDO

Vertical slice de infraestructura verificado de extremo a extremo:

1. **Estructura del repo** creada (backend / frontend / tests / nginx).
2. **Docker Compose** levanta 5 contenedores: `sqlserver`, `mongo`, `redis`,
   `backend`, `frontend`. Los 3 de datos con healthchecks.
3. **FastAPI** arranca con `/` y `/health`. El endpoint `/health` verifica conexión
   real a las 3 bases de datos.
4. **Frontend** mínimo (HTML/CSS/JS vanilla) que consume `/health` y muestra el
   estado de cada servicio.
5. **Tests** con pytest (3 tests, en verde).

**Verificación final lograda:**
```bash
curl http://localhost:8000/health
# {"status":"ok","services":{"sqlserver":true,"mongo":true,"redis":true}}
```
- Frontend `http://localhost:3000` → 3 servicios en verde.
- `python -m pytest -q` → 3 passed.

> ⚠️ **Alcance deliberado:** En Sprint 1 NO se integró Auth0 ni Claude API. Sus
> variables existen en `.env` como placeholders vacíos para sprints posteriores.

---

## ✅ Sprint 2 — Autenticación y Seguridad

Estrategia elegida: **HÍBRIDA**. Un switch `AUTH_MODE` decide el motor de auth:
- `AUTH_MODE=local` (actual): FastAPI emite y valida **JWT propios (HS256)**
  firmados con `SECRET_KEY`. No requiere servicios externos → se puede probar ya.
- `AUTH_MODE=auth0`: valida **JWT RS256 de Auth0** contra su JWKS público. El
  código ya está implementado; solo falta crear el tenant y rellenar el `.env`.

**Implementado y verificado:**
- `POST /auth/login` (modo local): usuario/contraseña → JWT. Usa
  `OAuth2PasswordRequestForm` (form-urlencoded).
- `GET /auth/me`: ruta **PROTEGIDA** de ejemplo; requiere `Authorization: Bearer`.
- Dependencia `get_current_user` (en `dependencies.py`) que protege rutas y
  funciona en ambos modos.
- Hash de contraseñas con **passlib + bcrypt**. El hash nunca se expone en la API.
- Frontend con **Login/Logout**: formulario, guarda el JWT en `localStorage`,
  lo adjunta como Bearer, auto-login si el token sigue válido, y oculta el panel
  de estado tras logout.
- 5 tests de auth (login ok/ko, ruta protegida con/sin token, token inválido).

**Usuarios demo (modo local, en memoria):**
| Usuario | Contraseña | Roles |
|---------|-----------|-------|
| `admin` | `admin123` | admin |
| `dba`   | `dba12345` | dba   |

> ⚠️ El almacén de usuarios (`services/users.py`) es **en memoria** y no persiste.
> Pensado para demo; reemplazar por tabla en SQL Server más adelante.

**Verificación lograda:**
```
POST /auth/login (admin/admin123)        → 200 + access_token
GET  /auth/me sin token                  → 401
GET  /auth/me con Bearer válido          → 200 {username, roles, ...}
POST /auth/login con password mala       → 401
python -m pytest -q                      → 8 passed
```

---

## 📐 Arquitectura

```
┌──────────────────────────────────────────────┐
│  FRONTEND  (HTML5 + JS vanilla + CSS)         │  localhost:3000 (nginx)
└───────────────┬──────────────────────────────┘
                │ REST (fetch /health)
┌───────────────▼──────────────────────────────┐
│  BACKEND  (Python 3.11 + FastAPI + Uvicorn)   │  localhost:8000
│  Sprint 1: rutas / y /health                  │
└───────────────┬──────────────────────────────┘
       ┌─────────┼──────────┐
   ┌───▼───┐ ┌───▼────┐ ┌───▼───┐
   │ SQL   │ │MongoDB │ │ Redis │
   │Server │ │  :27017│ │ :6379 │
   │ :1433 │ └────────┘ └───────┘
   └───────┘
SERVICIOS EXTERNOS (futuros): Anthropic Claude API, Auth0
```

---

## 🛠️ Stack Tecnológico (estado real)

### Backend (implementado)
- Python 3.11, FastAPI 0.115, Uvicorn 0.34
- pydantic 2.10 + pydantic-settings 2.7 (config por env)
- SQLAlchemy 2.0 + pyodbc 5.2 (SQL Server, ODBC Driver 18)
- pymongo 4.10 (MongoDB)
- redis 5.2 (redis-py)
- httpx (cliente/tests), pytest + pytest-asyncio

### Frontend (implementado)
- HTML5 + CSS3 + JavaScript vanilla. Servido por nginx:alpine.

### Bases de Datos (corriendo en Docker)
- SQL Server 2022 (`mcr.microsoft.com/mssql/server:2022-latest`)
- MongoDB 7
- Redis 7-alpine

### Pendiente (sprints futuros)
- Auth0 / JWT, Anthropic Claude API, Azure Key Vault, WebSocket,
  GitHub Actions CI/CD, Nginx como reverse proxy del backend.

---

## 📁 Estructura ACTUAL del Proyecto

```
DBAAssistant/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI: incluye routers health y auth, CORS
│   │   ├── config.py          # Pydantic Settings (lee .env) + settings de auth
│   │   ├── dependencies.py    # get_current_user (protege rutas) [Sprint 2]
│   │   ├── models/
│   │   │   └── auth.py        # Pydantic: Token, User, UserInDB [Sprint 2]
│   │   ├── routes/
│   │   │   ├── health.py      # GET /health → estado de las 3 DBs
│   │   │   └── auth.py        # POST /auth/login, GET /auth/me [Sprint 2]
│   │   └── services/
│   │       ├── db.py          # engines/clients + check_* (sqlserver/mongo/redis)
│   │       ├── auth.py        # hashing + JWT (HS256 local / RS256 Auth0) [Sprint 2]
│   │       └── users.py       # almacén de usuarios en memoria (demo) [Sprint 2]
│   ├── Dockerfile             # Debian bookworm + ODBC Driver 18
│   ├── requirements.txt
│   ├── env.example.txt        # plantilla de variables (NOTA: nombre no estándar)
│   └── .env                   # IGNORADO por git
├── frontend/
│   ├── index.html             # vistas login + app (protegida)
│   ├── css/
│   │   └── style.css          # estilos del panel + formulario de login
│   └── js/
│       ├── auth.js            # login/logout, JWT en localStorage, Bearer [Sprint 2]
│       └── app.js             # panel de estado (fetch a /health)
├── tests/
│   ├── conftest.py            # fixture: TestClient(app)
│   └── unit/
│       └── test_health.py     # 3 tests (root + health ok + health degraded)
├── nginx/                     # (carpeta creada, conf de proxy pendiente)
├── docker-compose.yml         # 5 servicios
├── pytest.ini                 # pythonpath=backend, testpaths=tests
├── .gitignore                 # ignora .env, __pycache__, .pytest_cache, etc.
├── .env                       # variables reales (raíz; IGNORADO por git)
├── CONTEXT.md                 # este archivo
├── TFI_DBA_Assistant_PerezMoreno.pdf
└── TFI_PEREZMORENO.pdf
```

---

## 🔐 Variables de Entorno

**Hay DOS `.env` relevantes:**
- **`/.env` (raíz):** el que usa `docker-compose` (directiva `env_file: .env`).
  Este es el que importa para levantar los contenedores.
- `backend/.env`: presente, pero el backend en Docker recibe sus vars vía
  `env_file` del compose, no por este archivo.

**Regla clave de hosts (causó el bug inicial):**
- Cuando el backend corre **dentro de Docker**, los hosts deben ser los **nombres
  de servicio** de compose, NO `localhost` ni el nombre del PC:
  - `SQL_SERVER_HOST=sqlserver`
  - `MONGODB_URI=mongodb://mongo:27017`
  - `REDIS_URL=redis://redis:6379/0`
- Si algún día corres el backend **fuera de Docker** (uvicorn local), entonces sí
  usarías `localhost`.

**Valores actuales relevantes (.env raíz):**
```env
CORS_ORIGINS=http://localhost:3000,http://localhost:8080   # OJO: necesita ://
SQL_SERVER_HOST=sqlserver
SQL_SERVER_PORT=1433
SQL_SERVER_USER=sa            # Sprint 1 usa 'sa' (login DBAAssistant aún no existe)
SQL_SERVER_PASSWORD=Marlb0r0  # = MSSQL_SA_PASSWORD del contenedor
SQL_SERVER_DATABASE=DBAAssistant
MONGODB_URI=mongodb://mongo:27017
MONGODB_DATABASE=DBAAssistant
REDIS_URL=redis://redis:6379/0
# Auth (Sprint 2):
AUTH_MODE=local                 # local | auth0
SECRET_KEY=<clave-aleatoria>    # firma HS256 en modo local
ACCESS_TOKEN_EXPIRE_MINUTES=60
AUTH0_DOMAIN= / AUTH0_CLIENT_ID= / AUTH0_CLIENT_SECRET= / AUTH0_AUDIENCE=
# Placeholders (Sprint 3+):
ANTHROPIC_API_KEY= / CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

---

## 🚀 Cómo Levantar el Entorno (local)

```bash
# 1. Build del backend (la 1ª vez o tras cambiar Dockerfile/requirements)
docker-compose build --no-cache backend

# 2. Levantar todo
docker-compose up -d

# 3. Verificar estado de contenedores
docker-compose ps           # los 5 en Up / healthy

# 4. Verificar API
curl http://localhost:8000/health   # esperado: status "ok"

# 5. Frontend
#    Abrir http://localhost:3000 (Ctrl+F5 para evitar caché)

# 6. Tests (desde la RAÍZ del repo, no desde tests/)
python -m pytest -q
```

**Puertos:** backend 8000 · frontend 3000 · SQL Server 1433 · Mongo 27017 · Redis 6379.

---

## ⚙️ Decisiones / Detalles Técnicos Importantes

### Dockerfile del backend (problema resuelto en Sprint 1)
- Base fijada a **`python:3.11-slim-bookworm`** (Debian 12). La `python:3.11-slim`
  pura ahora resuelve a Debian 13 (trixie), que **eliminó `apt-key`** → la build
  fallaba con `apt-key: not found` (exit 127).
- Instalación del ODBC Driver 18 con método moderno:
  `curl ... | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg` +
  línea `deb [signed-by=...] .../debian/12/prod bookworm main` (NO `apt-key`).

### Base de datos `DBAAssistant`
- El contenedor de SQL Server **NO crea la base automáticamente**. Se creó a mano:
  ```sql
  IF DB_ID('DBAAssistant') IS NULL CREATE DATABASE DBAAssistant;
  ```
- Vive en el volumen `sqlserver_data`. Sobrevive a `restart` y `up/down`, pero
  **se pierde con `docker-compose down -v`**.
- 🔜 Pendiente: script de init automático para no depender del comando manual.

### Health check
- `app/services/db.py` define `check_sqlserver()`, `check_mongo()`,
  `check_redis()`. Cada uno hace un ping y devuelve bool. Los errores se
  **silencian** (try/except) → si algo falla, no aparece en logs; hay que probar
  la conexión directa para depurar.

### Tests
- `pytest.ini` en la raíz define `pythonpath = backend` para que
  `from app.main import app` funcione.
- ❌ NO ejecutar `python conftest.py` (no es un script). Usar `python -m pytest`.
- Los tests **mockean** los `check_*` con `unittest.mock.patch`, así corren sin
  necesidad de las bases de datos reales (aptos para CI).

### Comandos en Git Bash (Windows)
- Al pasar rutas absolutas a `docker-compose exec` (p. ej. la ruta de `sqlcmd`),
  Git Bash las convierte y rompe el comando. Prefijar con `MSYS_NO_PATHCONV=1`.
- sqlcmd dentro del contenedor: `/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "<pwd>" -No -Q "..."`

---

## 🐞 Pendientes / Deuda Técnica (atender pronto)

1. ~~`frontend/css/style.csv` → renombrar a `style.css`.~~ ✅ RESUELTO (2026-06-14).
2. **`backend/env.example.txt` → renombrar a `.env.example`** (convención).
3. ~~`.gitignore` que ignore `.env`, `__pycache__/`, `.pytest_cache/`.~~ ✅ RESUELTO
   (2026-06-14). `.gitignore` creado; ambos `.env` verificados como ignorados y el
   `.env` nunca llegó a trackearse en git.
4. **Script de init de SQL Server** que cree la base `DBAAssistant` automáticamente.
5. **Faltan `__init__.py`** en varios paquetes (funciona por namespace packages,
   pero conviene añadirlos para evitar sorpresas).
6. **Carpeta `nginx/`** creada pero sin configurar como reverse proxy del backend.
7. **Login `sa`** se usa por simplicidad; crear usuario `DBAAssistant` con permisos
   acotados es trabajo de Sprint 2 (seguridad).
8. Warning inofensivo de pytest-asyncio (`asyncio_default_fixture_loop_scope` unset);
   se puede silenciar en `pytest.ini` si molesta.

---

## ➡️ Próximos Pasos

**Cierre de Sprint 2 (cuando haya tenant Auth0):**
- Crear tenant + aplicación en auth0.com (plan free).
- Rellenar `AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, `AUTH0_AUDIENCE` y poner
  `AUTH_MODE=auth0` en el `.env`; recrear el backend.
- Integrar el SDK de Auth0 en el frontend (login redirige a Auth0).

**Sprint 3 (Chat & Claude API):**
- Interfaz de chat (frontend) + WebSocket.
- Integración Anthropic Claude API + prompt engineering.
- Historial de chats en MongoDB.

**Deuda de seguridad arrastrada:**
- Persistir usuarios en SQL Server (hoy están en memoria).
- Crear login `DBAAssistant` en SQL Server con permisos mínimos (hoy se usa `sa`).

---

## 📝 Estándares de Código
- **Python:** snake_case, type hints (Pydantic), docstrings Google style,
  formateo con Black. Imports ordenados (stdlib / third-party / local).
- **JavaScript:** camelCase para variables/funciones, UPPER_CASE para constantes,
  Prettier/ESLint.
- **Git:** Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`).
  Ramas: `feature/*`, `bugfix/*`, `hotfix/*`.

---

## 📚 Referencias
- Documento modelo: `TFI_DBA_Assistant_PerezMoreno.pdf`
- Proyecto propio: `TFI_PEREZMORENO.pdf`
