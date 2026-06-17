# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import (
    audit, auth, cache, chat, connections, health, optimization, performance, schema, sql,
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
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