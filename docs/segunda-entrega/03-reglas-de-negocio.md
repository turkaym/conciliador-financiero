# Reglas de negocio propuestas

Esta es la fuente canónica de reglas. Todas tienen prioridad **MVP** y se aceptarían mediante el criterio de la misma fila.

| ID | Regla | Criterio de aceptación |
|---|---|---|
| RN-01 | Solo registros `PENDIENTE` o `CON_PROPUESTAS`, válidos y no duplicados generan propuestas. | Bajo bloqueo ordenado, ambos registros se revalidan justo antes de insertar; ningún inelegible ni recién conciliado deja una propuesta `GENERADA`. |
| RN-02 | Una propuesta y una conciliación vinculan exactamente un movimiento y un comprobante. | Cada vínculo conserva cardinalidad 1:1. |
| RN-03 | La coincidencia obligatoria es ARS + monto exacto + fecha inclusiva entre −3 y +3 días. | Fallar un criterio excluye la pareja. |
| RN-04 | La referencia normalizada solo ordena y explica; no altera el original ni habilita parejas inválidas. | Cambiar la similitud no modifica la elegibilidad. |
| RN-05 | Ninguna propuesta confirma automáticamente. | Toda conciliación identifica una confirmación humana. |
| RN-06 | Un registro no puede pertenecer a más de una conciliación activa. | Ante competencia, como máximo una operación se confirma. |
| RN-07 | Las propuestas terminales se conservan. Tras caducidad o reversión, una pareja nuevamente elegible puede crear otra; una `RECHAZADA` con igual versión y datos no reaparece sin cambio relevante o reapertura explícita. | Cada intento conserva historia y una regeneración rechazada idéntica se deniega salvo reapertura documentada. |
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
