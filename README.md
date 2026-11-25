# CONCILIADOR - Plataforma de conciliación financiera

Proyecto académico de la Tecnicatura Universitaria en Programación (UTN). La aplicación permite importar movimientos bancarios y comprobantes, detectar coincidencias, confirmar o revertir conciliaciones y conservar trazabilidad.

## Estado actual

El MVP está implementado y validado localmente. La rama de trabajo incorpora:

- Importación CSV con esquema resuelto automáticamente según la fuente.
- Validación estructural, normalización regional y deduplicación por fila.
- Consolidado persistente de movimientos y comprobantes.
- Propuestas automáticas sincronizadas al ingresar al módulo y mediante un botón manual.
- Conciliación automática y manual.
- Auditoría de conciliaciones activas, reversión y regeneración de coincidencias.
- Filtros de auditoría y exportación contable CSV Debe/Haber.
- Historial de eventos.

La publicación en Render puede corresponder a una revisión anterior hasta que esta rama sea integrada y desplegada.

## Acceso de demostración

- Usuario: `demo@conciliador.local`
- Contraseña: `Demo1234!`

Son credenciales y datos ficticios para demostración. No deben usarse con información financiera real.

## Funcionalidades

### Importar

El usuario selecciona el tipo y la fuente; la interfaz obtiene el único esquema activo compatible y muestra sus columnas esperadas. No se selecciona una plantilla manualmente.

Fuentes bancarias:

- Banco Nación, Banco Provincia, Santander, Galicia, BBVA, Banco Macro, ICBC y Supervielle.
- Naranja X y Mercado Pago.

Fuentes de comprobantes:

- Mercado Pago, Tienda Nube y ARCA.
- Facturas físicas previamente convertidas mediante OCR a CSV. La aplicación no procesa imágenes ni PDF.

El parser admite UTF-8 y CP1252, separadores coma, punto y coma o tabulación, fechas configuradas por fuente y decimales regionales. Los duplicados internos o históricos se omiten sin detener las demás filas.

### Consolidado

Incluye pestañas de Movimientos y Comprobantes con:

- Filtros por banco o entidad, fecha y estado conciliado.
- Ordenamiento y paginación.
- Persistencia del estado de cada pestaña por usuario en `localStorage`.

El antiguo módulo Pendientes fue eliminado de la navegación. Los registros no conciliados se consultan en Consolidado o en la selección manual de Propuestas.

### Propuestas

La pestaña **Automáticas** ejecuta el matcher al ingresar y también ofrece **Buscar coincidencias**. La sincronización es idempotente: no duplica propuestas generadas ni revive propuestas rechazadas.

La elegibilidad automática exige:

- Moneda `ARS`.
- Monto exacto.
- Diferencia de fecha de hasta tres días inclusive.

La referencia normalizada solo ordena y explica candidatos. La confirmación siempre requiere una acción humana. Al confirmar una propuesta se actualiza todo el listado para retirar alternativas que compartan registros y hayan quedado caducadas.

La pestaña **Manual** permite elegir un movimiento y un comprobante no conciliados y filtrarlos por fuente, fechas, monto, tolerancia, referencia y lote.

### Auditoría y reversión

Auditoría muestra conciliaciones activas con ambos registros. Permite filtrar por:

- Fecha de conciliación.
- Fecha del movimiento y del comprobante.
- Banco, entidad, monto, referencia y lote.
- Origen automático o manual.

Al deshacer:

- Una conciliación automática genera una propuesta nueva y trazable.
- Una conciliación manual libera ambos registros.
- Al volver a Automáticas, el matcher reevalúa todos los registros disponibles.
- La conciliación revertida desaparece de Auditoría activa, pero conserva su trazabilidad histórica.

La descarga CSV genera dos líneas por conciliación filtrada: movimiento bancario al Debe y comprobante al Haber, con la diferencia entre importes.

## Arquitectura

```text
React 19 + TypeScript + Vite
            |
FastAPI + Pydantic + SQLAlchemy
            |
        PostgreSQL 16
```

El backend es un monolito modular. PostgreSQL aplica integridad referencial, estados, unicidad de conciliaciones activas y protección transaccional.

## Ejecución local

1. Copiar `.env.example` a `.env` y definir `JWT_SECRET_KEY`.
2. Iniciar PostgreSQL:

   ```powershell
   docker compose up --wait
   ```

3. Instalar el backend:

   ```powershell
   backend\.venv\Scripts\python.exe -m pip install -e backend[test]
   ```

4. Inicializar o actualizar de forma idempotente la base:

   ```powershell
   Get-Content .env | Where-Object { $_ -match '^[^#][^=]*=' } | ForEach-Object {
     $name, $value = $_ -split '=', 2
     Set-Item -Path "Env:$($name.Trim())" -Value $value.Trim()
   }
   $env:PYTHONPATH='backend'
   backend\.venv\Scripts\python.exe -m app.initialize_database
   ```

5. Iniciar la API:

   ```powershell
   backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --env-file .env --host 127.0.0.1 --port 8000
   ```

6. Iniciar el frontend:

   ```powershell
   npm --prefix frontend install
   npm --prefix frontend run dev
   ```

La API queda en `http://localhost:8000`, el frontend en `http://localhost:5173` y `GET /health` debe responder `{"status":"healthy"}`.

## Pruebas

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests -q
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Última validación local de esta rama:

- 44 pruebas backend aprobadas.
- 17 pruebas frontend aprobadas.
- Build de producción aprobado.

## Datos de prueba

Los CSV están documentados en [docs/segunda-entrega/csv/README.md](docs/segunda-entrega/csv/README.md). Para probar coincidencias automáticas de Mercado Pago, importar:

- `mercado-pago-movimientos-prueba.csv`
- `mercado-pago-comprobantes-prueba.csv`

## Documentación

- [Guía funcional y de demostración](docs/conciliador-mvp-guide.md)
- [Alcance y módulos](docs/segunda-entrega/01-alcance-y-modulos.md)
- [Requerimientos](docs/segunda-entrega/02-requerimientos.md)
- [Reglas de negocio](docs/segunda-entrega/03-reglas-de-negocio.md)
- [Diseño de base de datos](docs/segunda-entrega/04-diseno-base-de-datos.md)
- [Contrato API](docs/segunda-entrega/09-contrato-api.md)
- [CSV de prueba](docs/segunda-entrega/csv/README.md)
- [Backend](backend/README.md)
- [Frontend](frontend/README.md)

## Limitaciones

- Proyecto académico, no preparado para datos financieros reales.
- Sin integraciones directas con bancos, Mercado Pago, Tienda Nube o ARCA.
- Sin OCR interno, inteligencia artificial ni confirmación autónoma.
- Solo conciliación 1:1 en ARS.
- Sin roles avanzados, recuperación de contraseña ni multi-tenancy.
