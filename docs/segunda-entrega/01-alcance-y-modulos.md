# Alcance y módulos del MVP

## Alcance implementado

| Nivel | Contenido |
|---|---|
| Implementado | Acceso pre-registrado; importación CSV por fuente; validación y deduplicación; ARS; conciliación 1:1 automática y manual; consolidado; auditoría; reversión; historial; exportación contable. |
| Extensible | Nuevas fuentes/esquemas, mejoras de ranking, procesamiento asíncrono y métricas. |
| Fuera de alcance | Integraciones reales, OCR interno, IA, egresos, multimoneda, relaciones 1:N/N:M, roles avanzados, multi-tenancy y uso productivo. |

## Módulos funcionales

| Módulo | Responsabilidad |
|---|---|
| Acceso | Autenticar al usuario demo y atribuir acciones. |
| Catálogos | Exponer bancos, entidades y esquemas versionados. |
| Importación | Recibir CSV, validar, normalizar y deduplicar. |
| Consolidado | Consultar movimientos y comprobantes con filtros persistentes. |
| Propuestas automáticas | Sincronizar, ordenar y explicar coincidencias elegibles. |
| Conciliación manual | Seleccionar explícitamente un movimiento y un comprobante disponibles. |
| Auditoría | Consultar activas, filtrar, exportar y deshacer conciliaciones. |
| Historial | Conservar eventos y detalles de decisiones/reversiones. |

## Correspondencia técnica

| Concepto | Backend | Frontend |
|---|---|---|
| Acceso | `backend/app/access` | `frontend/src/auth.tsx` |
| Importación | `backend/app/import_catalogs`, `imports`, `validation` | `frontend/src/modules/imports` |
| Consolidado | `backend/app/queries` | `frontend/src/modules/consolidated` |
| Propuestas | `backend/app/proposals` | `frontend/src/modules/proposals` |
| Conciliación y auditoría | `backend/app/reconciliation`, `audit` | `frontend/src/modules/proposals`, `reconciliation_history` |

El endpoint técnico `/pending` se conserva por compatibilidad, pero ya no tiene módulo visual. La experiencia vigente usa `/records` en Consolidado y en la selección manual.

## Recorrido funcional

1. El operador se autentica.
2. Selecciona tipo y fuente; el sistema resuelve el esquema sin selector de plantilla.
3. El CSV se procesa por filas y los duplicados se omiten.
4. Los registros válidos aparecen en Consolidado.
5. Automáticas sincroniza coincidencias al ingresar o mediante botón.
6. El operador confirma una propuesta o forma un par manual.
7. Auditoría permite filtrar, exportar y deshacer.
8. Una reversión libera registros; el matcher puede volver a proponerlos.

## Arquitectura

Monolito modular React/Vite → FastAPI/Pydantic/SQLAlchemy → PostgreSQL 16. Las operaciones de confirmación y reversión son transaccionales y revalidan disponibilidad antes de modificar estados.
