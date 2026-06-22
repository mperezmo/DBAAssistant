# CLAUDE.md — Guía para Claude Code (DBA Assistant)

> Punto de entrada para retomar el proyecto en cualquier sesión nueva.
> **Leé primero `CONTEXT.md`**: tiene el historial completo de sprints, decisiones,
> reglas de negocio, arquitectura y estado actual. Este archivo resume lo esencial.

## Qué es
DBA Assistant: app full-stack para administrar y optimizar **SQL Server** con IA
generativa (**Claude**), autenticación (**Auth0**), **MongoDB** y **Redis**.
Backend **FastAPI** (`backend/`) + frontend **React + Vite** (`frontend/`),
orquestado con **Docker Compose**. Diseño en `design/DBA Assistant.html`.

## Estado actual
- Sprints **1–8 ✅** (core completo; tags `v0.2.0 … v0.8.0`).
- **Sprint 9 ✅** Contexto de Negocio + IA: refinar "criollo"→profesional, y
  **chat-AGENTE** (Claude *tool use*) que elige la base solo, ejecuta SELECT
  (solo lectura, TOP 1000), muestra la tabla y exporta a CSV.
- **Sprint 10 ✅** **Workarounds** (biblioteca de remediación): catálogo de 6
  playbooks built-in (matar sesiones bloqueantes, rebuild de índices, update
  statistics, shrink de log, limpiar plan cache, checkpoint) + CRUD de
  workarounds custom (Mongo). Cada uno corre en **diagnóstico** (solo lectura) o
  **aplicar** (remediación real, AUTOCOMMIT), por conexión+base, auditado.
- **Sprint 10.1 ✅** Extensiones de Workarounds:
  - **Workaround de servicio (`start_sql_service`)**: inicia el servicio de SQL
    Server a nivel **Windows vía WinRM** (`services/host_control.py`, `pywinrm`),
    útil cuando el motor está caído (sin conexión T-SQL). Config WinRM por
    conexión en *Panel Admin* (`/connections/{id}/host-control`).
  - **Automatización por reglas** (`workaround_rules`): "si y solo si" el
    diagnóstico detecta el problema (≥ umbral), aplica la remediación. Motor
    `services/automation.py` (`workaround.auto`), botón **Evaluar ahora**
    (`/workarounds/rules/evaluate`) y **scheduler interno** opt-in
    (`AUTOMATION_ENABLED`, `services/scheduler.py`).
- **Pendientes (plan)** para las opciones de menú deshabilitadas:
  **Sprint 11 Alertas**, **Sprint 12 Dashboard/Inicio**.

## Cómo correr (desarrollo)
- `docker-compose up -d` — SQL Server (host `:14330`), Mongo `:27017`, Redis `:6379`,
  backend `:8000`, frontend `:3000`. Swagger en `http://localhost:8000/docs`.
- Tests: `python -m pytest` (unit + cobertura, ~64). Integración (stack arriba):
  `python -m pytest tests/integration -v`.
- Tras cambios de frontend: `docker-compose build frontend && docker-compose up -d frontend`.

## Cómo trabajamos (convenciones)
- **Por sprint**: backend real → conectar la página del diseño → tests (mock en unit)
  → auditar las acciones → commit (Conventional Commits) → `git push` → tag `vX.Y.0`.
- Todo endpoint va **protegido por auth** (`get_current_user`) y las acciones se
  **auditan** (`audit_repo.log`, acción tipo `recurso.accion`).
- Las funciones de datos operan **por (conexión, base)** vía
  `connections_repo.get_engine_for_db`. Las DMVs requieren `VIEW SERVER STATE`.
- **Nunca** commitear `.env`/secretos (están en `.gitignore`).
- Verificá CI verde con `gh run watch` tras push (workflow `ci.yml`).

## Arquitectura clave
- **Conexiones = instancias** (gestor dinámico en Mongo); se agregan en *Panel Admin*.
  El esquema se analiza por **base** (selector aparte).
- **Capa semántica**: *Contexto de Negocio* (`business_context`) alimenta el Sandbox
  y el **chat-agente** (le dice a la IA dónde está cada dato).
- **Chat** = agente con herramienta `run_query` (solo lectura): elige base, ejecuta,
  muestra tabla + **Exportar CSV** (`/sql/export`).
- **Caché Redis** de metadata (`services/cache.py`, con circuit breaker).
- **CI/CD**: `.github/workflows/` (ci, release a GHCR por tag, deploy-azure scaffold).
  Producción: `docker-compose.prod.yml`, `nginx/` reverse proxy, Key Vault opcional.

## Config / secretos
`.env` (gitignored): `SQL_SERVER_*`, `MONGODB_*`, `REDIS_URL`, `AUTH_MODE=auth0`
(+ `AUTH0_DOMAIN/CLIENT_ID/AUDIENCE`), `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`.
Automatización (Sprint 10.1, opcional): `AUTOMATION_ENABLED=false`,
`AUTOMATION_INTERVAL_SECONDS=60`. Credenciales WinRM: por conexión (Mongo, texto
plano dev/TFI; la API nunca devuelve la password).

## Docs
`CONTEXT.md` (estado + historial), `README.md`, `docs/USER_GUIDE.md`,
`docs/API.md`, `docs/DEPLOYMENT.md`.
