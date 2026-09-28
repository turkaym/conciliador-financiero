# Alcance y módulos propuestos

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

Se propone un monolito modular: React/Vite → API FastAPI/Pydantic → aplicación → dominio ← adaptadores SQLAlchemy/PostgreSQL; Alembic administraría la evolución futura. Las reglas permanecerían independientes de HTTP y ORM. La dirección de dependencias, los límites y la persistencia se amplían en [diseño de base de datos](04-diseno-base-de-datos.md) y [diagramas](06-diagramas.md).

## Recorrido funcional

1. El operador se autenticaría y seleccionaría fuente, plantilla y tipo compatibles.
2. El sistema calcularía la huella, detectaría archivos repetidos y validaría estructura y filas.
3. Conservaría originales; produciría datos normalizados o errores consultables.
4. Generaría propuestas solo para registros elegibles.
5. Una persona confirmaría o rechazaría; también podría revertir con motivo.
6. Pendientes e historial conservarían el origen, los estados, el actor y las decisiones.

Los criterios verificables están en [requerimientos](02-requerimientos.md); las restricciones del dominio, en [reglas de negocio](03-reglas-de-negocio.md).
