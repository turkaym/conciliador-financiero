# Reglas de negocio vigentes

| ID | Regla |
|---|---|
| RN-01 | Cada conciliación vincula exactamente un movimiento y un comprobante. |
| RN-02 | El matching automático exige ARS, monto exacto y diferencia de fecha inclusiva de ±3 días. |
| RN-03 | La referencia normalizada solo ordena y explica; no define elegibilidad. |
| RN-04 | Ninguna propuesta se confirma automáticamente. |
| RN-05 | Un registro no puede integrar más de una conciliación activa. |
| RN-06 | Confirmar una propuesta caduca todas las generadas que compartan alguno de sus registros. |
| RN-07 | Un rechazo es terminal para la misma pareja, regla y huella; no reaparece sin cambio relevante. |
| RN-08 | Una conciliación revertida conserva historia, pero deja de aparecer en Auditoría activa. |
| RN-09 | La reversión automática crea una propuesta nueva; nunca reutiliza la propuesta histórica. |
| RN-10 | La reversión manual libera ambos registros sin crear por sí sola una propuesta automática. La siguiente sincronización puede detectarla. |
| RN-11 | El matcher se ejecuta al importar, revertir automáticamente, abrir Automáticas o presionar Buscar coincidencias. Repetirlo es idempotente. |
| RN-12 | Un error o duplicado de fila no invalida las filas válidas del mismo lote. |
| RN-13 | Los duplicados históricos no crean otro movimiento/comprobante y referencian el original. |
| RN-14 | Rechazo y reversión exigen motivo; confirmación, rechazo y reversión registran actor y fecha. |
| RN-15 | La conciliación manual puede aceptar diferencias de fecha o monto porque representa una decisión explícita. |
| RN-16 | La exportación incluye únicamente conciliaciones activas que cumplen los filtros de Auditoría. |

## Estados

| Objeto | Estados/transiciones principales |
|---|---|
| Lote | `RECIBIDO → EN_VALIDACION → PROCESADO | PROCESADO_CON_ERRORES | PROCESADO_SIN_VALIDOS | FALLIDO`; `DUPLICADO` terminal. |
| Registro | `IMPORTADO → INVALIDO | PENDIENTE`; `PENDIENTE ↔ CON_PROPUESTAS`; `CON_PROPUESTAS → CONCILIADO`; reversión libera. |
| Propuesta | `GENERADA → CONFIRMADA | RECHAZADA | CADUCADA`. |
| Conciliación | `ACTIVA → REVERTIDA`. |

Los terminales históricos no se reabren. Cuando un par debe reaparecer se crea una propuesta nueva con su propia identidad y procedencia.
