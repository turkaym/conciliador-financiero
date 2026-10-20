# Reglas de negocio del MVP

Esta es la fuente canónica de reglas. Todas tienen prioridad **MVP** y su criterio de aceptación está en la misma fila.

| ID | Regla | Criterio de aceptación |
|---|---|---|
| RN-01 | Tras un lote con válidos o durante una reversión, cada registro habilitado se compara con pendientes opuestos históricos. Generar, confirmar y revertir bloquean todos los `registro_importado` involucrados por `id ASC` antes de revalidar. | `PROCESADO_SIN_VALIDOS`, `FALLIDO` y `DUPLICADO` no generan. Una `GENERADA` sobre un extremo conciliado se rechaza; una nueva `ACTIVA` caduca las incompatibles. El orden global evita deadlocks. |
| RN-02 | Una propuesta y una conciliación vinculan exactamente un movimiento y un comprobante. | Cada vínculo conserva cardinalidad 1:1. |
| RN-03 | La coincidencia obligatoria es ARS + monto exacto + fecha inclusiva entre −3 y +3 días. | Fallar un criterio excluye la pareja. |
| RN-04 | `ref-nfkd-v1` aplica NFKD, quita marcas, convierte a mayúsculas, cambia puntuación por espacio, colapsa/recorta y forma tokens únicos. Jaccard vale 0 con unión vacía; igualdad vacía es falsa. Ordena por exacta desc, Jaccard desc, diferencia absoluta de días asc e IDs asc. | Iguales datos/versiones producen igual orden; la referencia no habilita ni excluye. |
| RN-05 | Ninguna propuesta confirma automáticamente. | Toda conciliación identifica una confirmación humana. |
| RN-06 | Un registro no puede pertenecer a más de una conciliación activa ni a una nueva propuesta generada si ya está conciliado. | Bajo los locks ordenados y triggers de respaldo, ante competencia queda como máximo una `ACTIVA` y ninguna `GENERADA` incompatible. |
| RN-07 | Las propuestas terminales se conservan. Una `RECHAZADA` con igual pareja, `version_regla` y `huella_evaluacion` no reaparece; solo un cambio relevante o versión nueva crea otra evaluación. La pareja recién revertida también se omite con identidad idéntica. | Nunca se reabre una terminal; una identidad distinta permite una nueva propuesta trazable. |
| RN-08 | Rechazo y reversión exigen motivo no vacío; toda acción exige usuario autenticado y fecha. | La ausencia de cualquier dato deniega la operación. |
| RN-09 | Revertir es una transacción única: bloquea registros por ID ascendente y luego la conciliación, revalida `ACTIVA`, marca `REVERTIDA`, libera extremos, recompara, crea propuestas/eventos y confirma todo o nada. | No elimina historia ni reabre terminales; un fallo deshace estados, propuestas y auditoría. |
| RN-10 | La identidad del archivo usa bytes. Solo estados en curso o procesados reservan la huella; `FALLIDO` y `DUPLICADO` la liberan. La identidad de fila usa originales estables. | Un nuevo envío tras fallo puede reservar. Un `DUPLICADO` concurrente no se promociona si el dueño falla. |
| RN-11 | Un error de fila no invalida otras. Estructura reconocida y cero válidas termina `PROCESADO_SIN_VALIDOS`; estructura desconocida, plantilla inválida o fallo técnico termina `FALLIDO`. | Mixto, cero válidos y fallo tienen estados y códigos distintos. |
| RN-12 | Toda transición no declarada se rechaza sin cambios parciales. | Estado y datos permanecen iguales ante una transición inválida. |
| RN-13 | Cada propuesta declara origen `LOTE` o `REVERSION` y exactamente una referencia: lote disparador o conciliación revertida. | Origen nulo, doble o cruzado se rechaza; la creación queda auditada. |

## Estados permitidos

| Objeto | Transiciones |
|---|---|
| Lote | `RECIBIDO → EN_VALIDACION → PROCESADO | PROCESADO_CON_ERRORES | PROCESADO_SIN_VALIDOS | FALLIDO`; `DUPLICADO` nace directamente terminal; `FALLIDO` puede nacer directo ante plantilla desconocida |
| Registro | `IMPORTADO → INVALIDO | PENDIENTE`; `PENDIENTE ↔ CON_PROPUESTAS`; `CON_PROPUESTAS → CONCILIADO`; reversión a `PENDIENTE` o `CON_PROPUESTAS` |
| Propuesta | `GENERADA → CONFIRMADA | RECHAZADA | CADUCADA` |
| Conciliación | `ACTIVA → REVERTIDA` |

El [diagrama de estados](06-diagramas.md#7-estados) representa estas transiciones; esta tabla gobierna su interpretación textual.
