# Alcance y módulos del MVP

## Alcance priorizado

| Nivel | Contenido |
|---|---|
| MVP | Acceso de usuarios pre-registrados; CSV con plantillas conocidas; cobranzas ARS; conciliación 1:1; revisión humana; pendientes e historial; prueba de hasta 10.000 registros por carga. |
| Nice to have | Mapeo manual, búsqueda aproximada con `pg_trgm`, procesamiento asincrónico, dashboard y exportación. |
| Fuera de alcance | Egresos, multimoneda, relaciones 1:N o N:M, roles y administración avanzada, integraciones reales, OCR/IA, ERP, fiscalidad, multi-tenancy e infraestructura distribuida. |

El volumen de 10.000 registros define una futura prueba funcional, no un SLA ni un tiempo prometido. La coincidencia propuesta exige ARS, monto exacto y fecha inclusiva de ±3 días; la referencia solo ayuda a ordenar y explicar.

## Módulos y límites

| Módulo | Responsabilidad propuesta | No hace |
|---|---|---|
| Acceso básico | Autenticar y atribuir acciones a usuarios pre-registrados | Alta pública o roles avanzados |
| Catálogos de importación | Exponer fuentes y versiones de plantillas activas | Conectar bancos o sistemas externos |
| Importación | Recibir un CSV, calcular su huella y administrar el lote | Interpretar reglas de conciliación |
| Validación-normalización | Conservar originales, tipar datos y registrar errores | Alterar los valores recibidos |
| Propuestas | Buscar parejas elegibles y explicar criterios | Confirmar automáticamente |
| Revisión-conciliación | Confirmar, rechazar y revertir de forma atómica | Borrar decisiones previas |
| Pendientes-consultas | Filtrar registros por tipo, lote y estado | Modificar datos del dominio |
| Trazabilidad | Registrar cronología append-only junto con cada hecho | Sustituir las entidades operativas |

## Arquitectura objetivo

La arquitectura objetivo es un monolito modular: React/Vite → API FastAPI/Pydantic → aplicación → dominio ← adaptadores SQLAlchemy/PostgreSQL. Alembic administra la evolución futura. Las reglas permanecen independientes de HTTP y ORM. La dirección de dependencias, los límites y la persistencia se amplían en [diseño de base de datos](04-diseno-base-de-datos.md) y [diagramas](06-diagramas.md).

## Estado de trabajo

El relevamiento está **No iniciado**. El diseño documental está definido y la codificación del producto está **No iniciada**. Las responsabilidades siguientes expresan el comportamiento requerido, no software disponible.

## Recorrido funcional

1. El operador se autentica y selecciona fuente, plantilla y tipo compatibles.
2. El sistema calcula la huella, detecta archivos repetidos y valida estructura y filas.
3. Conserva originales y produce datos normalizados o errores consultables.
4. Al finalizar correctamente el lote, genera propuestas para nuevos elegibles contra pendientes opuestos históricos.
5. Una persona confirma o rechaza; una conciliación activa puede revertirse con motivo.
6. Pendientes e historial conservan el origen, los estados, el actor y las decisiones.

Los criterios verificables están en [requerimientos](02-requerimientos.md); las restricciones del dominio, en [reglas de negocio](03-reglas-de-negocio.md).
