# backend/Dockerfile
# Base fijada a Debian 12 (bookworm): Microsoft publica msodbcsql18 para esta
# versión y evita el problema de apt-key removido en Debian 13 (trixie).
FROM python:3.11-slim-bookworm

# Dependencias del sistema + ODBC Driver 18 de Microsoft (para pyodbc/SQL Server).
# Método moderno de claves: gpg --dearmor + signed-by (apt-key ya no existe).
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg unixodbc-dev gcc g++ ca-certificates \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]