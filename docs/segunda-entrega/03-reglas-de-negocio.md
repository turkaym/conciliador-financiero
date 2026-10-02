# Reglas de negocio del MVP

Esta es la fuente canónica de reglas. Todas tienen prioridad **MVP** y su criterio de aceptación está en la misma fila.

| ID | Regla | Criterio de aceptación |
|---|---|---|
| RN-01 | Al finalizar un lote procesado, cada nuevo `PENDIENTE` o `CON_PROPUESTAS` válido y no duplicado se compara automáticamente con todos los pendientes opuestos, incluso históricos. Generar y conciliar bloquean los dos `registro_importado` por `id` ascendente antes de revalidar. | `FALLIDO`/`DUPLICADO` no genera. Una nueva `GENERADA` se rechaza si un extremo tiene conciliación `ACTIVA`; una nueva `ACTIVA` caduca las demás `GENERADA` que compartan un extremo. El orden común evita deadlocks. |
| RN-02 | Una propuesta y una conciliación vinculan exactamente un movimiento y un comprobante. | Cada vínculo conserva cardinalidad 1:1. |
| RN-03 | La coincidencia obligatoria es ARS + monto exacto + fecha inclusiva entre −3 y +3 días. | Fallar un criterio excluye la pareja. |
| RN-04 | `ref-nfkd-v1` aplica NFKD, quita marcas, convierte a mayúsculas, cambia puntuación por espacio, colapsa/recorta y forma tokens únicos. Jaccard vale 0 con unión vacía; igualdad vacía es falsa. Ordena por exacta desc, Jaccard desc, diferencia absoluta de días asc e IDs asc. | Iguales datos/versiones producen igual orden; la referencia no habilita ni excluye. |
| RN-05 | Ninguna propuesta confirma automáticamente. | Toda conciliación identifica una confirmación humana. |
| RN-06 | Un registro no puede pertenecer a más de una conciliación activa ni a una nueva propuesta generada si ya está conciliado. | Bajo los locks ordenados y triggers de respaldo, ante competencia queda como máximo una `ACTIVA` y ninguna `GENERADA` incompatible. |
| RN-07 | Las propuestas terminales se conservan. Una `RECHAZADA` con igual versión y datos no reaparece; solo un cambio relevante de datos o `version_regla` crea una evaluación trazable nueva. | Cada intento conserva historia y una pareja rechazada idéntica permanece terminal. |
| RN-08 | Rechazo y reversión exigen motivo no vacío; toda acción exige usuario autenticado y fecha. | La ausencia de cualquier dato deniega la operación. |
| RN-09 | Revertir agrega historia, devuelve ambos registros a pendientes y puede caducar propuestas incompatibles. | No se elimina la conciliación ni sus eventos. |
| RN-10 | La identidad del archivo usa bytes; la de fila usa originales estables, nunca normalizados mutables. | Renormalizar no cambia la clave deduplicada. |
| RN-11 | Un error de fila no invalida otras; un error estructural que impide interpretar la plantilla falla el lote. | Lote mixto y lote estructuralmente inválido terminan en estados distintos. |
| RN-12 | Toda transición no declarada se rechaza sin cambios parciales. | Estado y datos permanecen iguales ante una transición inválida. |

## Estados permitidos

| Objeto | Transiciones |
|---|---|
| Lote | `RECIBIDO → EN_VALIDACION → PROCESADO | PROCESADO_CON_ERRORES | FALLIDO`; `RECIBIDO → DUPLICADO`; creación directa en `FALLIDO` solo ante plantilla desconocida |
| Registro | `IMPORTADO → INVALIDO | PENDIENTE`; `PENDIENTE ↔ CON_PROPUESTAS`; `CON_PROPUESTAS → CONCILIADO`; reversión a `PENDIENTE` o `CON_PROPUESTAS` |
| Propuesta | `GENERADA → CONFIRMADA | RECHAZADA | CADUCADA` |
| Conciliación | `ACTIVA → REVERTIDA` |

El [diagrama de estados](06-diagramas.md#7-estados) representa estas transiciones; esta tabla gobierna su interpretación textual.
