# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import (
    audit, auth, cache, chat, connections, health, optimization, performance, schema, sql,
)

settings = get_settings()

API_DESCRIPTION = """
Asistente inteligente para administración de bases de datos SQL Server.

**Autenticación:** todos los endpoints (salvo `/` y `/health`) requieren un JWT
`Bearer` (Auth0 RS256 o JWT local según `AUTH_MODE`).

Documentación interactiva: **/docs** (Swagger) y **/redoc**.
"""

TAGS_METADATA = [
    {"name": "health", "description": "Estado del servicio y de las bases (SQL/Mongo/Redis)."},
    {"name": "auth", "description": "Login (modo local) y perfil del usuario autenticado."},
    {"name": "connections", "description": "Alta/baja de conexiones a instancias SQL Server y descubrimiento de bases."},
    {"name": "schema", "description": "Metadata por conexión+base: tablas, columnas, índices, FKs (con caché)."},
    {"name": "performance", "description": "Monitoreo en vivo vía DMVs: CPU, memoria, sesiones, top queries."},
    {"name": "optimization", "description": "Recomendaciones de índices (faltantes / sin uso)."},
    {"name": "sql", "description": "Generación (IA) y ejecución controlada de SQL (preview/apply) + historial."},
    {"name": "chat", "description": "Chat con Claude e historial de conversaciones (MongoDB)."},
    {"name": "audit", "description": "Bitácora de acciones (quién/qué/cuándo)."},
    {"name": "cache", "description": "Estadísticas y limpieza de la caché Redis."},
]

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=API_DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    root_path=settings.root_path,  # "/api" detrás del reverse proxy en producción
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(connections.router)
app.include_router(schema.router)
app.include_router(performance.router)
app.include_router(audit.router)
app.include_router(sql.router)
app.include_router(cache.router)
app.include_router(optimization.router)


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "message": "DBA Assistant API running",
    }