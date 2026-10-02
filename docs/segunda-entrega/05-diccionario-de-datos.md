# Diccionario de datos físico

Fuente atributo por atributo del esquema PostgreSQL 16. `NN` indica `NOT NULL`; `—` indica que no aplica. Los nombres de FK/UQ/CHECK remiten a [`database/schema.sql`](../../database/schema.sql).

## Identidad y catálogos

| Tabla.atributo | Tipo | Nulable | Default | PK | FK | UQ | CHECK | Descripción |
|---|---|---:|---|---:|---|---|---|---|
| `usuario.id` | `BIGINT IDENTITY` | No | identidad | Sí | — | PK | — | Identificador del usuario pre-registrado. |
| `usuario.email` | `VARCHAR(254)` | No | — | No | — | `uq_usuario_email_ci` sobre `lower` | no vacío | Credencial de acceso sin distinción de mayúsculas. |
| `usuario.password_hash` | `TEXT` | No | — | No | — | — | no vacío | Hash seguro no recuperable de la contraseña. |
| `usuario.activo` | `BOOLEAN` | No | `TRUE` | No | — | — | — | Habilitación de acceso. |
| `usuario.creado_en` | `TIMESTAMPTZ` | No | `now()` | No | — | — | — | Alta en UTC. |
| `fuente_datos.id` | `BIGINT IDENTITY` | No | identidad | Sí | — | `uq_fuente_datos_id_tipo` con tipo | — | Identificador de procedencia. |
| `fuente_datos.tipo_origen` | `VARCHAR(20)` | No | — | No | — | `uq_fuente_datos_id_tipo` | `BANCO\|COMPROBANTES` | Familia de fuente. |
| `fuente_datos.codigo` | `VARCHAR(50)` | No | — | No | — | `uq_fuente_datos_codigo` | no vacío | Código estable. |
| `fuente_datos.nombre` | `VARCHAR(120)` | No | — | No | — | — | no vacío | Nombre visible. |
| `fuente_datos.activa` | `BOOLEAN` | No | `TRUE` | No | — | — | — | Disponibilidad para nuevas cargas. |
| `plantilla_importacion.id` | `BIGINT IDENTITY` | No | identidad | Sí | — | clave candidata con fuente/tipo | — | Identificador de plantilla versionada. |
| `plantilla_importacion.fuente_id` | `BIGINT` | No | — | No | `fuente_datos.id` | dos UQ compuestas | trigger fuente/tipo | Fuente compatible. |
| `plantilla_importacion.nombre` | `VARCHAR(120)` | No | — | No | — | con fuente/tipo/versión | no vacío | Nombre solicitado por el lote. |
| `plantilla_importacion.tipo` | `VARCHAR(20)` | No | — | No | — | dos UQ compuestas | `MOVIMIENTO\|COMPROBANTE` | Tipo canónico producido. |
| `plantilla_importacion.version` | `INTEGER` | No | — | No | — | con fuente/nombre/tipo | `> 0` | Versión inmutable. |
| `plantilla_importacion.activa` | `BOOLEAN` | No | `TRUE` | No | — | — | — | Elegibilidad para nuevas cargas. |
| `campo_plantilla.id` | `BIGINT IDENTITY` | No | identidad | Sí | — | — | — | Identificador del mapeo. |
| `campo_plantilla.plantilla_id` | `BIGINT` | No | — | No | `plantilla_importacion.id` cascada | con columna; con canónico | — | Plantilla propietaria. |
| `campo_plantilla.columna_origen` | `VARCHAR(120)` | No | — | No | — | por plantilla | no vacío | Cabecera exacta del CSV. |
| `campo_plantilla.campo_canonico` | `VARCHAR(80)` | No | — | No | — | por plantilla | no vacío | Campo de dominio destino. |
| `campo_plantilla.tipo_dato` | `VARCHAR(20)` | No | — | No | — | — | catálogo de cinco tipos | Tipo de validación. |
| `campo_plantilla.requerido` | `BOOLEAN` | No | `TRUE` | No | — | — | — | Obligatoriedad de la columna/valor. |
| `campo_plantilla.formato_fecha` | `VARCHAR(40)` | Sí | `NULL` | No | — | — | solo para `FECHA` | Patrón de fecha. |
| `campo_plantilla.separador_decimal` | `CHAR(1)` | Sí | `NULL` | No | — | — | solo para `DECIMAL` | Separador esperado. |

## Importación y validación

| Tabla.atributo | Tipo | Nulable | Default | PK | FK | UQ | CHECK | Descripción |
|---|---|---:|---|---:|---|---|---|---|
| `lote_carga.id` | `BIGINT IDENTITY` | No | identidad | Sí | — | `uq_lote_id_fuente_tipo` con fuente/tipo | distinto del original | Intento de carga. |
| `lote_carga.fuente_id` | `BIGINT` | No | — | No | `fuente_datos.id`; parte de FK a plantilla | `uq_lote_id_fuente_tipo`; `uq_lote_huella_original` | — | Fuente declarada y heredada por cada registro. |
| `lote_carga.plantilla_id` | `BIGINT` | Sí | `NULL` | No | `fk_lote_plantilla_compuesta` | — | nula solo en `FALLIDO` o su `DUPLICADO` | Plantilla resuelta. |
| `lote_carga.plantilla_solicitada` | `VARCHAR(120)` | No | — | No | — | — | no vacía | Representación textual del `template_id` recibido, aun si no resuelve. |
| `lote_carga.usuario_id` | `BIGINT` | No | — | No | `usuario.id` | — | — | Autor de la carga. |
| `lote_carga.tipo` | `VARCHAR(20)` | No | — | No | parte de FK a plantilla | `uq_lote_id_fuente_tipo`; `uq_lote_huella_original` | movimiento/comprobante | Tipo declarado y heredado por cada registro. |
| `lote_carga.nombre_archivo` | `VARCHAR(255)` | No | — | No | — | — | no vacío | Nombre informativo del archivo. |
| `lote_carga.huella_archivo` | `BYTEA` | No | — | No | — | `uq_lote_huella_original` parcial con fuente/tipo para todo no duplicado | 32 bytes | SHA-256 de bytes exactos; también la reserva un `FALLIDO`. |
| `lote_carga.estado` | `VARCHAR(30)` | No | `RECIBIDO` | No | — | condiciona UQ | seis estados; coherencia | Estado del intento. |
| `lote_carga.lote_original_id` | `BIGINT` | Sí | `NULL` | No | `lote_carga.id` | — | obligatorio solo en duplicado | Lote con bytes previos. |
| `lote_carga.recibido_en` | `TIMESTAMPTZ` | No | `now()` | No | — | — | — | Recepción UTC. |
| `lote_carga.finalizado_en` | `TIMESTAMPTZ` | Sí | `NULL` | No | — | — | obligatorio solo terminal | Fin UTC. |
| `registro_importado.id` | `BIGINT IDENTITY` | No | identidad | Sí | — | — | distinto del original | Fila persistida. |
| `registro_importado.lote_id` | `BIGINT` | No | — | No | `fk_registro_lote_fuente_tipo` → `lote_carga(id,fuente_id,tipo)` | con número de fila | — | Lote propietario; fuente y tipo deben coincidir. |
| `registro_importado.fuente_id` | `BIGINT` | No | — | No | `fuente_datos.id`; `fk_registro_lote_fuente_tipo` | clave elegible parcial | — | Procedencia idéntica a la del lote. |
| `registro_importado.numero_fila` | `INTEGER` | No | — | No | — | por lote | `> 1` | Número físico, incluida cabecera. |
| `registro_importado.tipo` | `VARCHAR(20)` | No | — | No | `fk_registro_lote_fuente_tipo` | clave elegible parcial | movimiento/comprobante | Tipo idéntico al del lote y subtipo esperado. |
| `registro_importado.estado` | `VARCHAR(30)` | No | `IMPORTADO` | No | — | condiciona UQ | cinco estados | Estado de fila. |
| `registro_importado.id_externo` | `VARCHAR(120)` | Sí | `NULL` | No | — | — | nulo o no vacío | Identidad aportada por fuente. |
| `registro_importado.clave_duplicado` | `BYTEA` | No | — | No | — | parcial fuente/tipo/clave | 32 bytes | SHA-256 estable de fila. |
| `registro_importado.registro_original_id` | `BIGINT` | Sí | `NULL` | No | `registro_importado.id` | — | implica `INVALIDO` | Primera fila equivalente. |
| `registro_importado.datos_originales` | `JSONB` | No | — | No | — | — | objeto; trigger inmutable | Valores recibidos. |
| `registro_importado.creado_en` | `TIMESTAMPTZ` | No | `now()` | No | — | — | — | Persistencia UTC. |
| `movimiento_bancario.registro_id` | `BIGINT` | No | — | Sí | `registro_importado.id` cascada | PK | subtipo diferible | Registro base. |
| `movimiento_bancario.fecha` | `DATE` | No | — | No | — | — | — | Fecha bancaria. |
| `movimiento_bancario.monto` | `NUMERIC(18,2)` | No | — | No | — | — | `> 0` | Crédito exacto. |
| `movimiento_bancario.moneda` | `CHAR(3)` | No | — | No | — | — | `ARS` | Moneda MVP. |
| `movimiento_bancario.referencia_normalizada` | `TEXT` | Sí | `NULL` | No | — | — | — | Copia normalizada versionada por propuesta. |
| `movimiento_bancario.es_credito` | `BOOLEAN` | No | — | No | — | — | verdadero | Dirección admitida. |
| `comprobante.registro_id` | `BIGINT` | No | — | Sí | `registro_importado.id` cascada | PK | subtipo diferible | Registro base. |
| `comprobante.fecha` | `DATE` | No | — | No | — | — | — | Fecha del comprobante. |
| `comprobante.monto` | `NUMERIC(18,2)` | No | — | No | — | — | `> 0` | Importe exacto. |
| `comprobante.moneda` | `CHAR(3)` | No | — | No | — | — | `ARS` | Moneda MVP. |
| `comprobante.referencia_normalizada` | `TEXT` | Sí | `NULL` | No | — | — | — | Copia normalizada versionada por propuesta. |
| `comprobante.clase` | `VARCHAR(20)` | No | — | No | — | — | `VENTA\|COBRO` | Clase admisible. |
| `error_validacion.id` | `BIGINT IDENTITY` | No | identidad | Sí | — | — | — | Error individual. |
| `error_validacion.lote_id` | `BIGINT` | No | — | No | `lote_carga.id` | — | — | Lote afectado. |
| `error_validacion.registro_id` | `BIGINT` | Sí | `NULL` | No | `registro_importado.id` | — | coherente con alcance | Fila afectada. |
| `error_validacion.alcance` | `VARCHAR(10)` | No | — | No | — | — | `LOTE\|FILA` | Nivel del error. |
| `error_validacion.campo` | `VARCHAR(120)` | Sí | `NULL` | No | — | — | — | Cabecera/campo afectado. |
| `error_validacion.codigo` | `VARCHAR(60)` | No | — | No | — | — | no vacío | Código estable de API. |
| `error_validacion.mensaje` | `TEXT` | No | — | No | — | — | no vacío | Explicación humana. |
| `error_validacion.registro_original_id` | `BIGINT` | Sí | `NULL` | No | `registro_importado.id` | — | — | Duplicado previo relacionado. |
| `error_validacion.creado_en` | `TIMESTAMPTZ` | No | `now()` | No | — | — | — | Detección UTC. |

## Propuestas, conciliación e historial

| Tabla.atributo | Tipo | Nulable | Default | PK | FK | UQ | CHECK | Descripción |
|---|---|---:|---|---:|---|---|---|---|
| `propuesta_conciliacion.id` | `BIGINT IDENTITY` | No | identidad | Sí | — | — | — | Evaluación candidata. |
| `propuesta_conciliacion.movimiento_id` | `BIGINT` | No | — | No | `movimiento_bancario.registro_id` | dos UQ parciales por pareja/versión | — | Extremo bancario. |
| `propuesta_conciliacion.comprobante_id` | `BIGINT` | No | — | No | `comprobante.registro_id` | dos UQ parciales por pareja/versión | — | Extremo contable. |
| `propuesta_conciliacion.estado` | `VARCHAR(20)` | No | `GENERADA` | No | — | condiciona UQ | cuatro estados; datos de decisión | Estado terminal o pendiente. |
| `propuesta_conciliacion.normalizador_version` | `VARCHAR(30)` | No | — | No | — | — | no vacío | `ref-nfkd-v1`. |
| `propuesta_conciliacion.version_regla` | `VARCHAR(30)` | No | — | No | — | dos UQ parciales | no vacía | Versión de elegibilidad/ranking. |
| `propuesta_conciliacion.score_referencia` | `NUMERIC(5,4)` | No | — | No | — | — | `0..1` | Jaccard. |
| `propuesta_conciliacion.coincidencia_exacta` | `BOOLEAN` | No | — | No | — | — | — | Igualdad no vacía normalizada. |
| `propuesta_conciliacion.diferencia_dias` | `SMALLINT` | No | — | No | — | — | `-3..3` | Comprobante menos movimiento. |
| `propuesta_conciliacion.explicacion` | `JSONB` | No | — | No | — | — | objeto | Componentes, origen y versiones. |
| `propuesta_conciliacion.motivo_decision` | `TEXT` | Sí | `NULL` | No | — | — | obligatorio al rechazar | Motivo humano. |
| `propuesta_conciliacion.decidida_por` | `BIGINT` | Sí | `NULL` | No | `usuario.id` | — | coherente con estado | Actor de confirmar/rechazar. |
| `propuesta_conciliacion.decidida_en` | `TIMESTAMPTZ` | Sí | `NULL` | No | — | — | coherente con estado | Decisión/caducidad UTC. |
| `propuesta_conciliacion.creado_en` | `TIMESTAMPTZ` | No | `now()` | No | — | — | — | Generación UTC. |
| `conciliacion.id` | `BIGINT IDENTITY` | No | identidad | Sí | — | — | — | Vínculo confirmado. |
| `conciliacion.propuesta_id` | `BIGINT` | No | — | No | `propuesta_conciliacion.id` | Sí | — | Propuesta confirmada única. |
| `conciliacion.movimiento_id` | `BIGINT` | No | — | No | `movimiento_bancario.registro_id` | parcial si activa | — | Extremo bancario. |
| `conciliacion.comprobante_id` | `BIGINT` | No | — | No | `comprobante.registro_id` | parcial si activa | — | Extremo contable. |
| `conciliacion.estado` | `VARCHAR(20)` | No | `ACTIVA` | No | — | condiciona UQ | activa/revertida | Estado del vínculo. |
| `conciliacion.confirmada_por` | `BIGINT` | No | — | No | `usuario.id` | — | — | Usuario confirmador. |
| `conciliacion.confirmada_en` | `TIMESTAMPTZ` | No | `now()` | No | — | — | — | Confirmación UTC. |
| `conciliacion.revertida_por` | `BIGINT` | Sí | `NULL` | No | `usuario.id` | — | trio completo si revertida | Usuario reversor, relación independiente. |
| `conciliacion.revertida_en` | `TIMESTAMPTZ` | Sí | `NULL` | No | — | — | trio completo si revertida | Reversión UTC. |
| `conciliacion.motivo_reversion` | `TEXT` | Sí | `NULL` | No | — | — | no vacío si revertida | Justificación obligatoria. |
| `evento_historial.id` | `BIGINT IDENTITY` | No | identidad | Sí | — | — | — | Evento append-only. |
| `evento_historial.usuario_id` | `BIGINT` | Sí | `NULL` | No | `usuario.id` | — | obligatorio en acción humana | Actor. |
| `evento_historial.lote_id` | `BIGINT` | Sí | `NULL` | No | `lote_carga.id` | — | exactamente un objetivo | Objetivo lote. |
| `evento_historial.registro_id` | `BIGINT` | Sí | `NULL` | No | `registro_importado.id` | — | exactamente un objetivo | Objetivo registro. |
| `evento_historial.propuesta_id` | `BIGINT` | Sí | `NULL` | No | `propuesta_conciliacion.id` | — | exactamente un objetivo | Objetivo propuesta. |
| `evento_historial.conciliacion_id` | `BIGINT` | Sí | `NULL` | No | `conciliacion.id` | — | exactamente un objetivo | Objetivo conciliación. |
| `evento_historial.tipo` | `VARCHAR(60)` | No | — | No | — | — | no vacío; reglas de actor/motivo | Tipo estable. |
| `evento_historial.motivo` | `TEXT` | Sí | `NULL` | No | — | — | obligatorio al rechazar/revertir | Justificación copiada. |
| `evento_historial.datos` | `JSONB` | No | `{}` | No | — | — | objeto | Metadatos del hecho. |
| `evento_historial.ocurrido_en` | `TIMESTAMPTZ` | No | `now()` | No | — | — | — | Ocurrencia UTC. |

## Índices y triggers

Además de PK/UQ, el SQL indexa las FK y los filtros de lote, registro, matching, propuestas e historial. `uq_lote_huella_original` garantiza una huella original para todo lote no `DUPLICADO`, aun `FALLIDO`; otros índices parciales garantizan una fila elegible, una propuesta `GENERADA` y una `RECHAZADA` por pareja/versión, y una conciliación activa por extremo.

El catálogo contiene ocho triggers: uno de coherencia plantilla–fuente–tipo; uno de inmutabilidad del original; tres constraint triggers diferibles de subtipo exacto (`tr_registro_subtipo_exacto`, `tr_movimiento_subtipo_exacto`, `tr_comprobante_subtipo_exacto`); `tr_propuesta_actualizacion_valida`, que restringe transiciones e impide cambiar pareja o evaluación; `tr_propuesta_generada_sin_conciliacion`; y `tr_conciliacion_activa_caduca_propuestas`. Los dos últimos bloquean los mismos registros por ID ascendente; el primero impide una `GENERADA` sobre una `ACTIVA` y el segundo exige la propuesta elegida `CONFIRMADA` y caduca otras `GENERADA` incompatibles.
