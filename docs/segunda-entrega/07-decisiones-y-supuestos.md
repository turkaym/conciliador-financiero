# Decisiones y supuestos vigentes

| Tema | Decisión |
|---|---|
| Arquitectura | Monolito modular síncrono para escala académica. |
| Alcance | ARS y conciliación 1:1. |
| Esquema de importación | Un esquema activo por fuente; la UI lo resuelve automáticamente. |
| Formatos bancarios | Esquema genérico cuando no hay especificación pública estable. |
| Facturas físicas | Se recibe CSV previamente producido por OCR; no se procesan imágenes. |
| Originales | JSON inmutable más subtipos normalizados. |
| Dinero | Decimal exacto. |
| Duplicados | Se omiten por fila y se conserva referencia al original. |
| Matching | Automático al importar y sincronizable al abrir el módulo o por botón. |
| Idempotencia | Solo `GENERADA` y `RECHAZADA` bloquean una evaluación idéntica; históricos revertidos/caducados pueden producir una propuesta nueva si los registros están libres. |
| Reversión | Nunca reutiliza una propuesta confirmada; crea una nueva cuando corresponde. |
| Manual | Permite diferencias explícitas y luego puede volver a ser evaluado automáticamente si se revierte. |
| Auditoría | La vista operativa muestra activas; la trazabilidad conserva revertidas. |
| Exportación | CSV Debe/Haber con dos líneas por conciliación. |
| Estado de UI | Filtros y pestañas se guardan por usuario en `localStorage`. |

## Supuestos

- Los archivos son ficticios o anonimizados.
- Los esquemas pueden evolucionar por versión sin editar datos históricos.
- Las integraciones reales requerirían autenticación, contratos y validación adicionales.
- La publicación en Render puede quedar detrás de la rama local hasta el siguiente despliegue.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Formato externo cambia | Catálogo versionado y error estructural explícito. |
| Propuesta visible queda obsoleta | Backend responde 409 y frontend refresca todo el listado. |
| Reversión reutiliza historia | Restricción única y nueva propuesta enlazada a la conciliación revertida. |
| Doble ejecución del matcher | Locks e idempotencia por estado, pareja, regla y huella. |
| Datos sensibles | Solo datos ficticios; secretos por variables de entorno. |
