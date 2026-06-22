# API — DBA Assistant

Documentación **interactiva** (siempre actualizada): `http://localhost:8000/docs`
(Swagger UI) y `http://localhost:8000/redoc`. El esquema OpenAPI está en
`http://localhost:8000/openapi.json`.

## Autenticación
Todos los endpoints (salvo `/` y `/health`) requieren `Authorization: Bearer <JWT>`.
- `AUTH_MODE=local`: el token lo emite `POST /auth/login`.
- `AUTH_MODE=auth0`: el token lo emite Auth0 (validado contra su JWKS, RS256).

## Endpoints

### Público
- `GET /` — info y versión.
- `GET /health` — estado de SQL Server / MongoDB / Redis.

### Auth
- `POST /auth/login` — (modo local) usuario/contraseña → JWT.
- `GET /auth/me` — perfil del usuario autenticado.

### Conexiones (instancias)
- `GET /connections` · `POST /connections` · `DELETE /connections/{id}`
- `POST /connections/test` — prueba sin guardar.
- `GET /connections/{id}/databases` — bases analizables (excluye sistema/ReportServer).

### Esquema (por conexión + base)
- `GET /schema/{conn}/{db}/overview`
- `GET /schema/{conn}/{db}/tables`
- `GET /schema/{conn}/{db}/tables/{schema}/{table}`
- Todas aceptan `?refresh=true` para saltear la caché.

### Performance (por conexión)
- `GET /performance/{conn}/metrics` · `/sessions` · `/top-queries`

### Optimización (por conexión + base)
- `GET /optimization/{conn}/{db}/missing-indexes`
- `GET /optimization/{conn}/{db}/unused-indexes`

### SQL
- `POST /sql/generate` — NL→T-SQL (Claude).
- `POST /sql/execute` — `mode=preview` (rollback) o `apply` (commit).
- `GET /sql/history` — historial de queries.

### Chat
- `POST /chat` · `GET /chat/conversations` · `GET /chat/conversations/{id}`

### Contexto de negocio (por conexión + base)
- `GET`/`PUT /context/{conn}/{db}` — descripción, reglas y glosario.
- `POST /context/{conn}/{db}/refine` — refina el contexto "en criollo" con IA.
- `GET`/`PUT /context/{conn}/{db}/tables/...` — contexto por tabla.

### Workarounds (biblioteca de remediación)
- `GET /workarounds` — catálogo (built-in + custom) con estadísticas de uso.
- `POST /workarounds` — crea un workaround custom (`diagnose_sql` debe ser SELECT).
- `DELETE /workarounds/{key}` — borra un workaround custom (los built-in no se borran).
- `POST /workarounds/{key}/run` — ejecuta sobre `connection_id`+`database`:
  `mode=diagnose` (solo lectura, muestra qué se vería afectado) o `mode=apply`
  (ejecuta la remediación real). Auditado (`workaround.run`).
- `GET /workarounds/runs` — historial de ejecuciones.

### Auditoría · Caché
- `GET /audit`
- `GET /cache/stats` · `POST /cache/clear`

## Códigos de estado típicos
- `401` sin token / token inválido · `404` recurso no encontrado ·
  `503` servicio externo no disponible (Claude/DB) · `400` SQL inválido.
