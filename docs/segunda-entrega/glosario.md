# Glosario

| Término | Definición |
|---|---|
| Conciliación | Vínculo 1:1 confirmado por una persona entre un movimiento y un comprobante. |
| Consolidado | Consulta de todos los registros válidos, conciliados o no, separada por tipo. |
| Comprobante | Venta/cobro susceptible de comparación con un movimiento. |
| Esquema | Plantilla versionada de columnas de una fuente; se resuelve automáticamente. |
| Fuente | Banco o entidad catalogada; no implica integración externa. |
| Huella de archivo | SHA-256 de los bytes usados para detectar un lote repetido. |
| Huella de fila | Identidad estable usada para duplicados internos/históricos. |
| Huella de evaluación | Identidad de pareja, datos y versiones del matcher. |
| Lote | Intento de importar un CSV. |
| Movimiento | Crédito bancario ARS importado. |
| Pendiente | Estado interno de un registro válido sin conciliación activa; no es un módulo visual. |
| Propuesta | Pareja candidata; no constituye conciliación. |
| Propuesta caducada | Alternativa que dejó de estar disponible porque uno de sus registros fue conciliado. |
| Reversión | Cambio auditado de `ACTIVA` a `REVERTIDA`; no borra historia. |
| Sincronización | Ejecución idempotente del matcher sobre registros disponibles. |
| `ref-nfkd-v1` | Normalizador de referencia NFKD, sin marcas, en mayúsculas, puntuación a espacio y tokens únicos. |

## Estados expuestos

La API y la interfaz usan los mismos valores en español que PostgreSQL:

- Lote: `RECIBIDO`, `EN_VALIDACION`, `PROCESADO`, `PROCESADO_CON_ERRORES`, `PROCESADO_SIN_VALIDOS`, `FALLIDO`, `DUPLICADO`.
- Registro: `IMPORTADO`, `INVALIDO`, `PENDIENTE`, `CON_PROPUESTAS`, `CONCILIADO`.
- Propuesta: `GENERADA`, `CONFIRMADA`, `RECHAZADA`, `CADUCADA`.
- Conciliación: `ACTIVA`, `REVERTIDA`.
