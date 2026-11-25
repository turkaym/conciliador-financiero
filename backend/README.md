# Backend

API FastAPI del conciliador financiero. Implementa autenticación JWT, catálogos por fuente, importación y deduplicación CSV, consolidados, matching, conciliación manual/automática, auditoría, reversión, exportación e historial.

## Requisitos

- Python 3.11+
- PostgreSQL 16
- Variables de `.env.example`, especialmente `DATABASE_URL` y `JWT_SECRET_KEY`

## Ejecución

Desde la raíz:

```powershell
backend\.venv\Scripts\python.exe -m pip install -e backend[test]
Get-Content .env | Where-Object { $_ -match '^[^#][^=]*=' } | ForEach-Object {
  $name, $value = $_ -split '=', 2
  Set-Item -Path "Env:$($name.Trim())" -Value $value.Trim()
}
$env:PYTHONPATH='backend'
backend\.venv\Scripts\python.exe -m app.initialize_database
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --env-file .env --host 127.0.0.1 --port 8000
```

`app.initialize_database` crea el esquema si no existe y aplica siempre `database/seed.sql`, que es idempotente.

## Módulos

| Carpeta | Responsabilidad |
|---|---|
| `access` | Login, JWT y usuario actual. |
| `import_catalogs` | Fuentes y esquemas activos. |
| `imports` | Lotes, archivo, validación y duplicados. |
| `validation` | Parseo y normalización por fuente. |
| `queries` | Consolidado y endpoint técnico de pendientes. |
| `proposals` | Matcher, sincronización y explicación. |
| `reconciliation` | Confirmación, manual, auditoría, reversión y exportación. |
| `audit` | Eventos históricos. |

## Rutas destacadas

- `POST /api/v1/batches`
- `GET /api/v1/records`
- `POST /api/v1/proposals/sync`
- `POST /api/v1/proposals/{id}/confirm`
- `POST /api/v1/reconciliations/manual`
- `GET /api/v1/reconciliations`
- `GET /api/v1/reconciliations/export.csv`
- `POST /api/v1/reconciliations/{id}/reverse`

## Pruebas

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests -q
```

Última validación: 44 pruebas aprobadas.
