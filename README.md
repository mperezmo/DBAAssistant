# DBA Assistant

Asistente inteligente para **administración y optimización de bases de datos SQL Server**,
con IA generativa (Claude), autenticación (Auth0/JWT) y una UI moderna.

> Proyecto full-stack: **FastAPI** (backend) + **React/Vite** (frontend) +
> **SQL Server / MongoDB / Redis**, todo orquestado con **Docker Compose**.

## ✨ Funcionalidades

| Módulo | Qué hace |
|--------|----------|
| **Chat IA** | Conversá con Claude sobre tus bases (genera SQL, explica, recomienda). |
| **Conexiones** | Gestor de instancias SQL Server (Panel Admin); descubre sus bases. |
| **Esquema de BD** | Tablas, columnas, índices y FKs por base (con caché Redis). |
| **Monitoreo** | DMVs en vivo: CPU, memoria, sesiones, top queries, anomalías. |
| **Sandbox SQL** | Generá SQL con IA y ejecutalo controlado: *preview* (rollback) / *apply* (commit) + historial. |
| **Optimización** | Índices faltantes (CREATE sugerido) y sin uso (DROP sugerido). |
| **Auditoría** | Bitácora de acciones (quién/qué/cuándo) en MongoDB. |
| **Caché** | Redis para metadata, con stats e invalidación. |

## 🚀 Quickstart (desarrollo)

```bash
git clone https://github.com/mperezmo/DBAAssistant.git
cd DBAAssistant

cp backend/env.example.txt .env        # completar valores (SQL_SERVER_PASSWORD, etc.)
docker-compose up -d --build           # levanta SQL Server, Mongo, Redis, backend y frontend

# Frontend:  http://localhost:3000
# API:       http://localhost:8000      ·  Swagger: http://localhost:8000/docs
```

Para el chat y la generación de SQL, agregá tu `ANTHROPIC_API_KEY` al `.env`.
Para login con Auth0, ver `docs/DEPLOYMENT.md`.

## 🧪 Tests

```bash
python -m pytest                 # unit tests + cobertura (53 tests)
python -m pytest tests/integration -v   # integration (requiere el stack levantado)
```

## 🛠️ Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy + pyodbc, PyMongo, redis-py, PyJWT, Anthropic SDK.
- **Frontend:** React 18 + Vite, `@auth0/auth0-react`.
- **Datos:** SQL Server 2022, MongoDB 7, Redis 7.
- **DevOps:** Docker Compose, GitHub Actions (CI + release a GHCR), Nginx, Azure (scaffold).

## 📚 Documentación

- `docs/USER_GUIDE.md` — guía de uso de cada pantalla.
- `docs/API.md` — referencia de la API.
- `docs/DEPLOYMENT.md` — despliegue a producción (Azure, CI/CD, secretos).
- `CONTEXT.md` — contexto del proyecto y estado de los sprints.

## 📦 Estado

Sprints 1-7 ✅ · Sprint 8 (testing & docs) en curso. Releases tageadas `vX.Y.Z`.
