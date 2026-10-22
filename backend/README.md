# Backend

Backend modular de FastAPI para el MVP de conciliacion financiera. El acceso usa
 un usuario pre-registrado y tokens JWT Bearer. MVP-03 agrega catálogos activos y
 recepción autenticada de lotes CSV; el procesamiento de filas se implementa en
 MVP-04.

## Requisitos

- Python 3.11+
- Docker Compose

## Configuracion local

Copie `.env.example` como `.env` y reemplace `JWT_SECRET_KEY` fuera de un entorno
local. La configuracion de demo documenta `demo@conciliador.local` y
`Demo1234!`; no reutilice estas credenciales fuera de desarrollo.

Inicialice PostgreSQL 16 desde la raiz del repositorio:

```text
docker compose up --wait
```

Los scripts `database/schema.sql` y `database/seed.sql` se ejecutan en ese orden
al crear un volumen nuevo. Para repetir una inicializacion limpia, use
`docker compose down -v` unicamente sobre el volumen local de este proyecto.

## Ejecutar la API

Desde la raiz del repositorio, instale las dependencias en `backend/.venv` y
ejecute:

```text
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

El endpoint `GET /health` devuelve `{"status":"healthy"}`. El login esta en
`POST /api/v1/auth/login` y recibe `{ "email": "...", "password": "..." }`.

## Pruebas

Desde la raiz:

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Las pruebas de acceso cubren login valido, rechazo uniforme de credenciales
invalidas y validacion basica de tokens protegidos. Las pruebas de MVP-03 cubren
catálogos, recepción/consulta de lotes y límites de autenticación y request.
