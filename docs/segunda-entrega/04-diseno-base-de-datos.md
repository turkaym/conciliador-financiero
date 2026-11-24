# Diseño de base de datos

## Criterios

El diseño usa PostgreSQL 16 porque el dominio requiere cardinalidad 1:1, integridad referencial, control concurrente y trazabilidad transaccional. Los importes usan `NUMERIC(18,2)`, las fechas de negocio `DATE`, los eventos `TIMESTAMPTZ` en UTC y los estados `VARCHAR` con `CHECK`. El [SQL](../../database/schema.sql) gobierna la implementación física y el [diccionario](05-diccionario-de-datos.md) la explica atributo por atributo.

## Modelo conceptual

- `Usuario` atribuye lotes, eventos, confirmaciones y reversiones mediante relaciones independientes.
- `FuenteDatos` identifica procedencia, tiene plantillas versionadas y no representa una integración externa.
- `PlantillaImportacion` define campos y procesa lotes resolubles.
- `LoteCarga` conserva todo intento y el `template_id` solicitado; `FALLIDO` y `DUPLICADO` pueden carecer de plantilla resuelta. Un duplicado nace terminal y señala al dueño concurrente de la huella.
- `RegistroImportado` conserva JSON original inmutable y tiene un único subtipo cuando es válido.
- `PropuestaConciliacion` une un movimiento y un comprobante, conserva huella de evaluación y procedencia XOR por lote o reversión; `Conciliacion` materializa la confirmación humana.
- `ErrorValidacion` explica fallos de lote o fila; `EventoHistorial` conserva una cronología transversal.

## Integridad y deduplicación

La huella de archivo es SHA-256 de sus bytes exactos. La clave de fila es SHA-256 de versión de algoritmo y componentes encuadrados por longitud: fuente, tipo e ID externo original; sin ID, campos originales estables ordenados por plantilla. No usa valores normalizados mutables.

El índice parcial `uq_lote_huella_original` reserva la huella solo para `RECIBIDO`, `EN_VALIDACION`, `PROCESADO`, `PROCESADO_CON_ERRORES` y `PROCESADO_SIN_VALIDOS`; `FALLIDO` y `DUPLICADO` conservan auditoría sin reservar. Otro índice reserva una clave para registros no `INVALIDO`. Los UQ de propuesta usan pareja, `version_regla` y `huella_evaluacion`; esta última es SHA-256 de fechas, montos, monedas, referencias originales y `normalizador_version`, encuadrados por longitud. Así se suprime una evaluación idéntica y se permite otra justificada. Cada extremo participa como máximo en una conciliación `ACTIVA`.

La procedencia exige `origen_tipo=LOTE` con solo `lote_origen_id`, o `origen_tipo=REVERSION` con solo `conciliacion_revertida_id`. Dos FK y dos índices parciales hacen consultable el origen. Como `conciliacion` referencia a `propuesta_conciliacion`, la FK inversa se agrega con `ALTER TABLE` después de crear ambas tablas.

`uq_lote_id_fuente_tipo (id, fuente_id, tipo)` es la clave candidata referenciada por `fk_registro_lote_fuente_tipo (lote_id, fuente_id, tipo)`: una fila no puede declarar fuente o tipo distintos de su lote.

## Operaciones atómicas previstas

| Operación | Límite transaccional |
|---|---|
| Importar | Una transacción corta intenta reservar `(fuente_id,tipo,huella_archivo)`. Un conflicto crea directamente `DUPLICADO` terminal con evento y `lote_original_id`. Si el dueño falla libera la huella; el duplicado no se promociona y un nuevo envío puede reservar. Estructura reconocida sin filas válidas termina `PROCESADO_SIN_VALIDOS`. |
| Generar propuestas | Tras el commit de un lote con válidos o durante reversión, bloquea registros por `id` ascendente, revalida y recién entonces inserta `GENERADA`. `tr_propuesta_generada_sin_conciliacion` repite el lock y rechaza extremos con conciliación `ACTIVA`, rechazos idénticos y la pareja revertida con identidad idéntica. |
| Confirmar | Lee sin lock los IDs inmutables de la pareja, bloquea ambos `registro_importado` por `id` ascendente y solo entonces bloquea la propuesta. Revalida que siga `GENERADA`, la cambia a `CONFIRMADA` y crea la conciliación. `tr_conciliacion_activa_caduca_propuestas` exige esa propuesta confirmada y caduca toda otra `GENERADA` que comparta un extremo, dentro del mismo commit. Generación y confirmación usan idéntico recurso y orden para evitar deadlocks. |
| Rechazar | Bloquea la propuesta, exige motivo y agrega estado y evento en el mismo commit. |
| Revertir | Lee IDs inmutables, reúne extremos/candidatos, bloquea todos los registros por `id ASC`, luego la conciliación y revalida `ACTIVA`. Marca `REVERTIDA`, libera extremos, omite la pareja revertida idéntica y rechazos idénticos, recompara e inserta propuestas `REVERSION` y eventos en un solo commit. Cualquier error revierte todo. |

## Originales y normalizados

`datos_originales` conserva el objeto recibido sin modificación semántica y no participa directamente en matching. Los adaptadores de plantilla producen campos tipados en los subtipos. Tres constraint triggers diferibles, sobre el registro y ambos subtipos, consultan estado/tipo actuales al final de la transacción: todo estado distinto de `INVALIDO` exige exactamente el subtipo indicado y `INVALIDO` exige ninguno. Así se admite `IMPORTADO → INVALIDO` junto con el borrado del subtipo, y se rechazan un segundo subtipo o el borrado del único. Otro trigger protege la inmutabilidad del original.

## Evolución futura

Alembic podría separar revisiones por dependencias: usuarios/fuentes, plantillas, lotes, registros, decisiones e índices. Un downgrade debería validar compatibilidad antes de recrear restricciones antiguas y abortar con diagnóstico antes que perder datos. Esto es una estrategia propuesta, no una migración existente.
