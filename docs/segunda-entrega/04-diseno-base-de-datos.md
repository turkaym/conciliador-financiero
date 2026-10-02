# Diseño de base de datos

## Criterios

El diseño usa PostgreSQL 16 porque el dominio requiere cardinalidad 1:1, integridad referencial, control concurrente y trazabilidad transaccional. Los importes usan `NUMERIC(18,2)`, las fechas de negocio `DATE`, los eventos `TIMESTAMPTZ` en UTC y los estados `VARCHAR` con `CHECK`. El [SQL](../../database/schema.sql) gobierna la implementación física y el [diccionario](05-diccionario-de-datos.md) la explica atributo por atributo.

## Modelo conceptual

- `Usuario` atribuye lotes, eventos, confirmaciones y reversiones mediante relaciones independientes.
- `FuenteDatos` identifica procedencia, tiene plantillas versionadas y no representa una integración externa.
- `PlantillaImportacion` define campos y procesa lotes resolubles.
- `LoteCarga` conserva todo intento y el `template_id` solicitado; `FALLIDO` y su posterior `DUPLICADO` pueden carecer de plantilla resuelta. Contiene registros o señala el lote original de un duplicado.
- `RegistroImportado` conserva JSON original inmutable y tiene un único subtipo cuando es válido.
- `PropuestaConciliacion` une un movimiento y un comprobante; `Conciliacion` materializa la confirmación humana.
- `ErrorValidacion` explica fallos de lote o fila; `EventoHistorial` conserva una cronología transversal.

## Integridad y deduplicación

La huella de archivo es SHA-256 de sus bytes exactos. La clave de fila es SHA-256 de versión de algoritmo y componentes encuadrados por longitud: fuente, tipo e ID externo original; sin ID, campos originales estables ordenados por plantilla. No usa valores normalizados mutables.

El índice único parcial `uq_lote_huella_original` reserva la huella de todo primer lote no `DUPLICADO`, incluso si queda `FALLIDO` sin plantilla; cada envío posterior se registra como `DUPLICADO` y apunta a ese primer lote. Otro índice reserva una clave solo para registros no `INVALIDO`; además hay una única propuesta `GENERADA` por pareja/versión y cada movimiento/comprobante participa como máximo en una conciliación `ACTIVA`. Los estados terminales permanecen históricos. El email tiene índice único funcional sobre `lower(email)`.

`uq_lote_id_fuente_tipo (id, fuente_id, tipo)` es la clave candidata referenciada por `fk_registro_lote_fuente_tipo (lote_id, fuente_id, tipo)`: una fila no puede declarar fuente o tipo distintos de su lote.

## Operaciones atómicas previstas

| Operación | Límite transaccional |
|---|---|
| Importar | Una transacción corta intenta reservar `(fuente_id, tipo, huella_archivo)` para todo primer lote, incluso `FALLIDO` por `template_id` desconocido. Un conflicto se registra como `DUPLICADO` con `lote_original_id`. Con plantilla resoluble, otra transacción procesa filas; ante fallo inesperado, revierte solo el procesamiento y una nueva transacción corta marca el lote `FALLIDO` con error `LOTE` y evento. |
| Generar propuestas | Tras el commit de un lote `PROCESADO` o `PROCESADO_CON_ERRORES`, bloquea ambos `registro_importado` por `id` ascendente, revalida y recién entonces inserta `GENERADA`. `tr_propuesta_generada_sin_conciliacion` repite el lock y rechaza la escritura si cualquier extremo tiene conciliación `ACTIVA`. |
| Confirmar | Lee sin lock los IDs inmutables de la pareja, bloquea ambos `registro_importado` por `id` ascendente y solo entonces bloquea la propuesta. Revalida que siga `GENERADA`, la cambia a `CONFIRMADA` y crea la conciliación. `tr_conciliacion_activa_caduca_propuestas` exige esa propuesta confirmada y caduca toda otra `GENERADA` que comparta un extremo, dentro del mismo commit. Generación y confirmación usan idéntico recurso y orden para evitar deadlocks. |
| Rechazar | Bloquea la propuesta, exige motivo y agrega estado y evento en el mismo commit. |
| Revertir | Bloquea conciliación y registros, exige motivo y recalcula pendientes sin borrar historia. |

## Originales y normalizados

`datos_originales` conserva el objeto recibido sin modificación semántica y no participa directamente en matching. Los adaptadores de plantilla producen campos tipados en los subtipos. Tres constraint triggers diferibles, sobre el registro y ambos subtipos, consultan estado/tipo actuales al final de la transacción: todo estado distinto de `INVALIDO` exige exactamente el subtipo indicado y `INVALIDO` exige ninguno. Así se admite `IMPORTADO → INVALIDO` junto con el borrado del subtipo, y se rechazan un segundo subtipo o el borrado del único. Otro trigger protege la inmutabilidad del original.

## Evolución futura

Alembic podría separar revisiones por dependencias: usuarios/fuentes, plantillas, lotes, registros, decisiones e índices. Un downgrade debería validar compatibilidad antes de recrear restricciones antiguas y abortar con diagnóstico antes que perder datos. Esto es una estrategia propuesta, no una migración existente.
