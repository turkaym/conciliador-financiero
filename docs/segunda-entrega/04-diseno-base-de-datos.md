# Diseño propuesto de base de datos

## Criterios

Se propone PostgreSQL relacional porque el dominio requiere cardinalidad 1:1, integridad referencial, control concurrente y trazabilidad transaccional. Los importes usarían `NUMERIC(18,2)`, las fechas de negocio `DATE`, los eventos `TIMESTAMPTZ` en UTC y los estados `VARCHAR` con `CHECK`. El [diccionario](05-diccionario-de-datos.md) es la fuente canónica de campos y restricciones.

## Modelo conceptual

- `Usuario` atribuiría lotes y decisiones.
- `FuenteDatos` identificaría procedencia; tendría plantillas versionadas y no representaría una integración externa.
- `PlantillaImportacion` definiría campos y procesaría lotes resolubles.
- `LoteCarga` conservaría todo intento y la plantilla solicitada; solo un `FALLIDO` podría carecer de plantilla resuelta. Contendría registros o señalaría el lote original de un duplicado.
- `RegistroImportado` conservaría JSON original inmutable y tendría un único subtipo cuando fuese válido.
- `PropuestaConciliacion` uniría un movimiento y un comprobante; `Conciliacion` materializaría la confirmación humana.
- `ErrorValidacion` explicaría fallos de lote o fila; `EventoHistorial` conservaría una cronología transversal.

## Integridad y deduplicación

La huella de archivo sería SHA-256 de sus bytes exactos. La clave de fila sería SHA-256 de versión de algoritmo y componentes encuadrados por longitud: fuente, tipo e ID externo original; sin ID, campos originales estables ordenados por plantilla. No usaría valores normalizados mutables.

Índices únicos parciales reservarían una huella solo para lotes con plantilla resuelta y no `DUPLICADO`, una clave solo para registros no `INVALIDO`, una única propuesta `GENERADA` por pareja/versión y cada movimiento/comprobante solo para conciliaciones `ACTIVA`. Los estados terminales de propuesta permanecerían históricos. Los `FALLIDO` sin plantilla no ocuparían la huella. El email tendría índice único funcional sobre `lower(email)`.

## Operaciones atómicas previstas

| Operación | Límite transaccional |
|---|---|
| Importar | Una transacción corta persistiría y confirmaría primero el intento. Con plantilla resoluble, otra transacción procesaría filas y reservaría claves mediante `ON CONFLICT`; ante fallo inesperado, revertiría solo el procesamiento y una nueva transacción corta marcaría el lote `FALLIDO` con error `LOTE` y evento. La plantilla desconocida se persistiría directamente como `FALLIDO`. |
| Generar propuestas | Bloquearía ambos registros en orden de ID y revalidaría elegibilidad antes de insertar una nueva `GENERADA` contra su índice parcial. Los estados terminales no se sobrescribirían: caducidad o reversión permitiría otra fila histórica si la pareja vuelve a ser elegible; un rechazo idéntico exigiría cambio relevante o reapertura explícita. Confirmación usaría el mismo orden y todo conflicto revertiría la operación. |
| Confirmar | `FOR UPDATE` bloquearía propuesta y registros en orden estable; se revalidaría elegibilidad antes de crear conciliación, estados, caducidades y evento en un commit. |
| Rechazar | Bloquearía la propuesta, exigiría motivo y agregaría estado y evento en el mismo commit. |
| Revertir | Bloquearía conciliación y registros, exigiría motivo y recalcularía pendientes sin borrar historia. |

## Originales y normalizados

`datos_originales` conservaría el objeto recibido sin modificación semántica y no participaría directamente en matching. Los adaptadores de plantilla producirían campos tipados en los subtipos. Un trigger diferible comprobaría que un registro válido tenga exactamente el subtipo indicado y que uno inválido no lo tenga; permisos y trigger protegerían la inmutabilidad del original.

## Evolución futura

Alembic podría separar revisiones por dependencias: usuarios/fuentes, plantillas, lotes, registros, decisiones e índices. Un downgrade debería validar compatibilidad antes de recrear restricciones antiguas y abortar con diagnóstico antes que perder datos. Esto es una estrategia propuesta, no una migración existente.
