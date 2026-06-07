# DBA Assistant - Project Context

## 📋 Visión General
**Nombre del Proyecto:** DBA Assistant  
**Tipo:** Aplicación Web Full-Stack  
**Objetivo Principal:** Asistente inteligente para administración y optimización de bases de datos usando IA generativa (Claude API)

---

## 🎯 Descripción del Proyecto
Desarrollar una aplicación web que permita a DBAs (Database Administrators) interactuar de forma natural con sus bases de datos, generando queries SQL automáticas, realizando análisis de rendimiento, y obteniendo recomendaciones de optimización mediante Claude API.

**Usuarios Objetivo:**
- Database Administrators (DBAs)
- Desarrolladores
- Analistas de datos

---

## 📐 Arquitectura de la Aplicación

```
┌─────────────────────────────────────────────────────────┐
│                    CAPA CLIENTE (Frontend)              │
│  HTML5 + JavaScript + CSS (Responsive UI)              │
└────────────────┬────────────────────────────────────────┘
                 │ REST API / WebSocket
┌────────────────▼────────────────────────────────────────┐
│              CAPA BACKEND (Python FastAPI)              │
│  • Autenticación (Auth0 + JWT)                          │
│  • Gestión de Chat                                      │
│  • Generación de SQL (Claude API)                       │
│  • Análisis de Bases de Datos                           │
│  • Ejecución de Queries                                 │
└────────────────┬────────────────────────────────────────┘
                 │
     ┌───────────┼───────────┬──────────────┐
     │           │           │              │
┌────▼──┐  ┌────▼────┐ ┌───▼─────┐  ┌────▼────┐
│  SQL  │  │MongoDB  │ │  Redis  │  │ Azure   │
│Server │  │  (Chat  │ │ (Cache) │  │  Vault  │
│2019+  │  │ History)│ │         │  │(Secrets)│
└───────┘  └─────────┘ └─────────┘  └─────────┘

┌─────────────────────────────────────────────────────────┐
│         SERVICIOS EXTERNOS                              │
│  • Anthropic Claude API (LLM)                           │
│  • Auth0 (Autenticación)                                │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Stack Tecnológico

### Frontend
- **HTML5, CSS3, JavaScript (Vanilla)**
- Alternativa: Vue.js o React (opcional)
- Responsive Design (Mobile-First)
- WebSocket para actualizaciones en tiempo real

### Backend
- **Python 3.11+**
- **FastAPI** (Framework web asincrónico)
- **Uvicorn** (ASGI Server)
- **SQLAlchemy** (ORM para SQL Server)
- **PyMongo** (Driver MongoDB)
- **Redis** (Cliente Python redis-py)

### Bases de Datos
- **SQL Server 2019+** (Datos principales, schemas, tablas)
- **MongoDB** (Historial de chats, logs)
- **Redis** (Cache de queries frecuentes, metadata)

### Seguridad & Autenticación
- **Auth0** (OAuth 2.0, OpenID Connect)
- **JWT** (JSON Web Tokens)
- **Azure Key Vault** (Gestión de credenciales)

### Integración IA
- **Anthropic Claude API** (Modelo: Claude 3.5 Sonnet o Superior)
- Manejo de tokens, costos, rate limiting

### DevOps
- **Docker & Docker Compose**
- **GitHub Actions** (CI/CD)
- **Azure Container Registry** (Registry)
- **Azure App Service** (Hosting)
- **Nginx** (Reverse Proxy)

---

## 📁 Estructura del Proyecto

```
DBAAssistant/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # Punto de entrada FastAPI
│   │   ├── config.py               # Configuración (variables entorno)
│   │   ├── models/                 # Modelos de datos
│   │   ├── routes/                 # Rutas API
│   │   ├── services/               # Lógica de negocio
│   │   ├── utils/                  # Funciones auxiliares
│   │   └── dependencies.py         # Dependencias FastAPI
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── css/
│   │   ├── style.css
│   │   └── responsive.css
│   ├── js/
│   │   ├── app.js
│   │   ├── chat.js
│   │   ├── auth.js
│   │   └── api.js
│   └── assets/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API_DOCUMENTATION.md
│   ├── DATABASE_SCHEMA.md
│   └── SETUP.md
├── docker-compose.yml
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── tests/
│   ├── unit/
│   └── integration/
├── .env.example
├── README.md
├── CONTEXT.md                      # Este archivo
└── CONTRIBUTING.md
```

---

## 🔐 Variables de Entorno

```env
# Backend
PYTHON_ENV=development
DEBUG=True
SECRET_KEY=your_secret_key_here

# Base de Datos SQL Server
SQL_SERVER_HOST=localhost
SQL_SERVER_PORT=1433
SQL_SERVER_USER=sa
SQL_SERVER_PASSWORD=YourPassword123!
SQL_SERVER_DATABASE=DBAAssistant

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=dba_assistant

# Redis
REDIS_URL=redis://localhost:6379

# Auth0
AUTH0_DOMAIN=your_domain.auth0.com
AUTH0_CLIENT_ID=your_client_id
AUTH0_CLIENT_SECRET=your_client_secret

# Claude API
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Azure (Opcional)
AZURE_VAULT_URL=https://your-vault.vault.azure.net/
AZURE_SUBSCRIPTION_ID=your_subscription_id

# App Settings
APP_NAME=DBA Assistant
APP_VERSION=1.0.0
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

---

## 🎬 Sprints Planificados

### Sprint 1: Fundamentos e Infraestructura (2-3 semanas)
- [ ] Setup del repositorio y estructura
- [ ] Configuración de Docker Compose
- [ ] Base de datos SQL Server inicial
- [ ] FastAPI project setup
- [ ] Frontend básico (HTML/CSS)
- [ ] Variables de entorno

### Sprint 2: Autenticación y Seguridad (1-2 semanas)
- [ ] Integración Auth0
- [ ] JWT implementation
- [ ] Login/Logout UI
- [ ] Rutas protegidas

### Sprint 3: Chat & Claude API (2-3 semanas)
- [ ] Chat interface (frontend)
- [ ] WebSocket setup
- [ ] Claude API integration
- [ ] Prompt engineering
- [ ] MongoDB chat history

### Sprint 4: Análisis de BD (2 semanas)
- [ ] Lectura de metadata (SQL Server)
- [ ] Análisis de performance
- [ ] Detección de anomalías
- [ ] Auditoría

### Sprint 5: Generación y Ejecución SQL (2-3 semanas)
- [ ] SQL generation from prompts
- [ ] Query validation
- [ ] Ejecución controlada
- [ ] Rollback/transacciones
- [ ] Historial de queries

### Sprint 6: Cache & Optimización (1-2 semanas)
- [ ] Redis cache implementation
- [ ] Performance monitoring
- [ ] Query optimization

### Sprint 7: DevOps & Deployment (1-2 semanas)
- [ ] GitHub Actions CI/CD
- [ ] Docker images
- [ ] Azure deployment

### Sprint 8: Testing & Docs (1-2 semanas)
- [ ] Unit tests
- [ ] Integration tests
- [ ] API documentation
- [ ] User guide

---

## 📝 Estándares de Código

### Python
```python
# Naming: snake_case
def get_user_data():
    pass

# Imports: Organized (stdlib, third-party, local)
import os
from typing import List

import fastapi
from sqlalchemy import create_engine

from app.models import User
```

- **Linter:** Black
- **Type hints:** Sí (Pydantic)
- **Docstrings:** Google style

### JavaScript
```javascript
// Naming: camelCase for variables/functions
function getUserData() {
  // code
}

// Constants: UPPER_CASE
const API_BASE_URL = 'http://localhost:8000';
```

- **Linter:** ESLint
- **Format:** Prettier

### Git Workflow
- **Branches:** `feature/*, bugfix/*, hotfix/*`
- **Commits:** Conventional Commits
  - `feat: add new feature`
  - `fix: correct bug`
  - `docs: update documentation`
  - `refactor: code improvement`

---

## 🔗 Componentes Principales

### 1. Chat Interface
- Interfaz conversacional con Claude
- Historial persistente
- Validación de prompts

### 2. SQL Generator
- Genera SQL automáticos
- Valida sintaxis
- Preview antes de ejecutar

### 3. Database Analyzer
- Lectura de tablas, índices, esquemas
- Estadísticas de rendimiento
- Sugerencias de optimización

### 4. Query Executor
- Ejecución controlada
- Transacciones
- Logging de cambios

### 5. Cache Layer
- Redis para queries frecuentes
- Invalidación automática

---

## 🚀 Cómo Empezar (Local Development)

```bash
# 1. Clonar repositorio
git clone https://github.com/mperezmo/DBAAssistant.git
cd DBAAssistant

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 3. Levantar servicios
docker-compose up -d

# 4. Instalar dependencias backend
cd backend
pip install -r requirements.txt

# 5. Ejecutar migraciones (si aplica)
python -m alembic upgrade head

# 6. Iniciar servidor backend
uvicorn app.main:app --reload

# 7. Abrir frontend
# Abre http://localhost:3000 (o el puerto configurado)
```

---

## 📚 Referencias Importantes

- **Documento Modelo:** `TFI_DBA_Assistant_PerezMoreno.pdf`
- **Tu Proyecto:** `TFI_PEREZMORENO.pdf`
- **Arquitectura Visual:** Imagen incluida en el repo

---

## 🔄 Próximos Pasos

1. **Llenar placeholders:** Actualizar este documento con detalles específicos
2. **Crear issues:** Convertir sprints en issues de GitHub
3. **Comenzar Sprint 1:** Setup inicial
4. **Integración con Claude:** Para desarrollo automático

---

## ✅ Checklist de Setup Inicial

- [ ] Repositorio clonado
- [ ] Docker instalado
- [ ] Variables de entorno configuradas
- [ ] SQL Server corriendo
- [ ] MongoDB corriendo
- [ ] Redis corriendo
- [ ] Backend funciona en localhost:8000
- [ ] Frontend funciona en localhost:3000
- [ ] Auth0 configurado (opcional para dev)
- [ ] Claude API key obtenida

---

## 📞 Soporte

Para preguntas sobre este proyecto, consulta la documentación en `/docs` o crea un issue en GitHub.

**Última actualización:** 2026-06-07  
**Versión:** 1.0.0 (Setup)
