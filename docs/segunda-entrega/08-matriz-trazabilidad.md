# Matriz de trazabilidad vigente

| Requisitos | Módulo | Rutas principales | Evidencia |
|---|---|---|---|
| RF-01 | Acceso | `POST /auth/login` | Pruebas de autenticación. |
| RF-02–RF-04 | Importación | `/catalog/*`, `POST /batches`, `/batches/{id}/errors` | Fixtures válidos, inválidos y duplicados. |
| RF-05 | Consolidado | `GET /records` | Pruebas de filtros, pestañas y persistencia. |
| RF-06 | Propuestas | `POST /proposals/sync`, `GET /proposals` | Sincronización inicial/manual e idempotencia. |
| RF-07 | Decisiones | `POST /proposals/{id}/confirm|reject` | Confirmación, rechazo y conflicto 409. |
| RF-08 | Manual | `POST /reconciliations/manual` | Selección de ambos tipos y validación de propietario. |
| RF-09–RF-10 | Auditoría/reversión | `GET /reconciliations`, `POST /reconciliations/{id}/reverse` | Reaparición de pares automáticos y manuales. |
| RF-11 | Exportación | `GET /reconciliations/export.csv` | Dos líneas Debe/Haber y filtros. |
| RF-12 | Historial | `GET /history`, `GET /reconciliations/{id}` | Eventos y detalle. |
| RF-13 | Frontend | `localStorage` por usuario | Pruebas de remount y persistencia. |

## Evidencia ejecutable

- `backend/tests`: 44 pruebas.
- `frontend/tests`: 17 pruebas.
- `npm --prefix frontend run build`: build de producción.
- `database/schema.sql`: esquema inicial.
- `database/seed.sql`: catálogo y actualizaciones idempotentes.

Esta matriz demuestra correspondencia entre requisitos, módulos, rutas y pruebas. No representa certificación productiva ni uso con datos reales.
