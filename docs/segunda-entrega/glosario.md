# Glosario

| Término | Definición propuesta |
|---|---|
| Conciliación | Vínculo 1:1 creado por confirmación humana entre un movimiento y un comprobante. |
| Comprobante | Registro de venta o cobro que puede compararse con un crédito bancario. |
| Error | Incumplimiento de plantilla, campo, formato, dominio o duplicidad. |
| Fuente de datos | Procedencia catalogada de un archivo; no implica integración externa. |
| Huella | SHA-256 usado para identificar contenido de archivo o componentes estables de una fila. |
| Huella de evaluación | SHA-256 de datos relevantes encuadrados por longitud y normalizador; junto con la pareja y `rule_version` identifica una evaluación. |
| Lote | Intento de importar un único CSV de movimientos o comprobantes. |
| Movimiento | Crédito bancario en ARS susceptible de conciliación. |
| Normalizado | Representación tipada y comparable, separada del valor original. |
| Original | Dato recibido que se conserva inmutable. |
| Pendiente | Registro válido sin conciliación activa, aunque tenga propuestas. |
| Plantilla | Definición versionada de columnas, tipos y campos canónicos de un CSV conocido. |
| Propuesta | Pareja candidata movimiento–comprobante; no constituye conciliación. |
| Procedencia de propuesta | Origen exclusivo `LOTE` o `REVERSION` y su única referencia disparadora. |
| `ref-nfkd-v1` | Normalizador versionado de referencias: NFKD, sin marcas, mayúsculas, puntuación a espacio, espacios colapsados y tokens únicos. |
| Registro | Movimiento o comprobante perteneciente a un lote. |
| Reversión | Cambio auditado de una conciliación activa a revertida; no borra historia. |
| SLA | Compromiso de nivel de servicio; no se define uno para el volumen académico. |

Los nombres exactos de estados se encuentran en [reglas de negocio](03-reglas-de-negocio.md#estados-permitidos).

## Estados SQL ↔ API

| Objeto | SQL/documentación | API |
|---|---|---|
| Lote | `RECIBIDO` | `RECEIVED` |
| Lote | `EN_VALIDACION` | `VALIDATING` |
| Lote | `PROCESADO` | `PROCESSED` |
| Lote | `PROCESADO_CON_ERRORES` | `PROCESSED_WITH_ERRORS` |
| Lote | `PROCESADO_SIN_VALIDOS` | `PROCESSED_WITHOUT_VALID_ROWS` |
| Lote | `FALLIDO` | `FAILED` |
| Lote | `DUPLICADO` | `DUPLICATE` |
| Registro | `IMPORTADO` | `IMPORTED` |
| Registro | `INVALIDO` | `INVALID` |
| Registro | `PENDIENTE` | `PENDING` |
| Registro | `CON_PROPUESTAS` | `WITH_PROPOSALS` |
| Registro | `CONCILIADO` | `RECONCILED` |
| Propuesta | `GENERADA` | `GENERATED` |
| Propuesta | `CONFIRMADA` | `CONFIRMED` |
| Propuesta | `RECHAZADA` | `REJECTED` |
| Propuesta | `CADUCADA` | `EXPIRED` |
| Conciliación | `ACTIVA` | `ACTIVE` |
| Conciliación | `REVERTIDA` | `REVERSED` |
