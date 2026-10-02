# Contrato HTTP `/api/v1`

Contrato previo a codificación para el monolito modular. Todas las operaciones salvo login requieren autenticación. JSON usa UTF-8, nombres `snake_case`, fechas de negocio `YYYY-MM-DD` y tiempos UTC RFC 3339. Los IDs son enteros positivos y los importes se serializan como cadenas decimales.

## Convenciones

Las listas responden `{ "page": 1, "page_size": 25, "total": 0, "items": [] }`. `page >= 1`; `page_size` admite `1..100` y vale `25` por defecto. Orden estable: criterio declarado y luego `id ASC`.

El modelo API traduce nombres físicos sin cambiar su significado: `normalizador_version`→`normalizer_version`, `version_regla`→`rule_version`, `score_referencia`→`reference_score`, `coincidencia_exacta`→`exact_match`, `diferencia_dias`→`day_difference` y `explicacion`→`ranking`.

Los errores usan:

```json
{"code":"CODIGO_ESTABLE","message":"Explicación","field":"campo_opcional","details":{},"trace_id":"uuid"}
```

| HTTP | Uso |
|---:|---|
| 400 | Request/multipart/parámetro mal formado. |
| 401 | Credencial ausente o inválida. |
| 404 | Recurso inexistente o no visible. |
| 409 | Estado, duplicidad o concurrencia incompatible. |
| 422 | Regla de dominio o campo semánticamente inválido. |
| 500 | Fallo inesperado; `trace_id` permite correlación sin filtrar secretos. |

## Acceso y catálogos

| Método y ruta | Entrada | Respuesta | Errores | RF |
|---|---|---|---|---|
| `POST /api/v1/auth/login` | JSON `{email,password}` | `200 {access_token,token_type:"bearer",expires_in,user:{id,email}}` | 400, 401, 422 | RF-01 |
| `GET /api/v1/catalog/sources` | Query `type?=MOVIMIENTO\|COMPROBANTE` | Lista `{id,code,name,type}` activa | 400, 401 | RF-02 |
| `GET /api/v1/catalog/templates` | Query `source_id,type` | Lista `{id,name,type,version,columns[]}` compatible | 400, 401, 404 | RF-02 |

Login nunca informa si el email existe. El token y su almacenamiento se definirán durante codificación; el contrato no expone hashes.

## Lotes, errores y pendientes

### Crear lote

`POST /api/v1/batches` recibe `multipart/form-data`: `source_id` (ID), `template_id` (ID exacto del catálogo), `type` (`MOVIMIENTO|COMPROBANTE`) y `file` (un CSV). Nombre y versión son informativos en `GET /catalog/templates`; la selección y resolución usan exclusivamente `template_id`. Responde `202` con:

```json
{"id":31,"status":"PROCESSED_WITH_ERRORS","requested_template_id":17,"template":{"id":17,"name":"bank","version":1},"file_name":"movimientos.csv","received_at":"2026-05-01T12:00:00Z"}
```

La implementación puede responder cuando termina el procesamiento síncrono aunque conserve `202` como aceptación del intento. Un `template_id` inexistente, inactivo o incompatible persiste lote `FAILED`, conserva el ID recibido en `plantilla_solicitada`, deja `plantilla_id NULL` y agrega un error `UNKNOWN_TEMPLATE` de alcance `LOTE`, consultable por `/errors`. Todo primer lote no `DUPLICATE`, incluido ese `FAILED`, reserva los bytes; cualquier repetición posterior produce `DUPLICATE` con `original_batch_id` y sin filas. Errores: 400 multipart/CSV ilegible, 401, 404 fuente, 409 conflicto de catálogo, 422 tipo/archivo. Cubre RF-02–RF-06.

| Método y ruta | Entrada/filtros | Respuesta | Errores | RF |
|---|---|---|---|---|
| `GET /api/v1/batches/{batch_id}` | Path ID | `{id,source,template?:{id,name,version},requested_template_id,type,file_name,status,totals,original_batch_id?,received_at,finished_at?}` | 401, 404 | RF-02, RF-03, RF-06 |
| `GET /api/v1/batches/{batch_id}/errors` | `page,page_size,scope?,field?` | Lista de `{id,scope,row_number?,field?,code,message,original_record_id?,created_at}` | 400, 401, 404 | RF-03, RF-06 |
| `GET /api/v1/pending` | `type?,batch_id?,state?,page,page_size` | Lista ordenada por `created_at,id` de `{record_id,type,batch_id,external_id?,date,amount,currency,reference_original,state,cause}` | 400, 401, 404 | RF-07 |

Los estados API en inglés mapean 1:1 a los estados SQL documentados; la tabla de mapeo queda en el glosario. La respuesta nunca sustituye ni modifica el original.

## Propuestas

Las propuestas nacen automáticamente cuando un lote termina `PROCESSED` o `PROCESSED_WITH_ERRORS`. Cada registro nuevo elegible se compara con todos los pendientes opuestos, incluidos lotes anteriores. Un lote `FAILED` o `DUPLICATE` no dispara comparación.

`GET /api/v1/proposals` acepta `status?`, `batch_id?`, `page`, `page_size`; ordena por `exact_match DESC`, `reference_score DESC`, `absolute_day_difference ASC`, `movement_id ASC`, `receipt_id ASC`. Devuelve ítems resumidos con IDs, fechas, montos, estado, score y versiones. RF-08, RF-09.

`GET /api/v1/proposals/{proposal_id}` devuelve:

```json
{
  "id": 81,
  "status": "GENERATED",
  "movement": {"record_id": 11, "batch_id": 3, "date": "2026-04-10", "amount": "1500.00", "currency": "ARS", "reference_original": "FACTURA 100"},
  "receipt": {"record_id": 24, "batch_id": 7, "date": "2026-04-11", "amount": "1500.00", "currency": "ARS", "reference_original": "Factura-100"},
  "ranking": {"exact_match": true, "reference_score": "1.0000", "day_difference": 1, "normalizer_version": "ref-nfkd-v1", "rule_version": "match-v1", "movement_normalized": "FACTURA 100", "receipt_normalized": "FACTURA 100", "movement_tokens": ["100","FACTURA"], "receipt_tokens": ["100","FACTURA"]},
  "origin": {"trigger_batch_id": 7, "generated_at": "2026-04-24T10:00:00Z"},
  "decision": null
}
```

Errores: 401, 404. La referencia explica y ordena; ARS, monto exacto y fecha ±3 días determinan elegibilidad.

### Decisiones

| Método y ruta | Entrada | Respuesta | Errores | RF |
|---|---|---|---|---|
| `POST /api/v1/proposals/{proposal_id}/confirm` | JSON vacío `{}` | `200 {proposal:{id,status:"CONFIRMED",decided_by,decided_at},reconciliation:{id,status:"ACTIVE"}}` | 401, 404, 409 estado/carrera, 422 inelegible | RF-10 |
| `POST /api/v1/proposals/{proposal_id}/reject` | JSON `{reason}` no vacío | `200 {id,status:"REJECTED",reason,decided_by,decided_at}` | 401, 404, 409 terminal, 422 motivo | RF-11 |

Generar y confirmar comparten protocolo: dentro de la transacción bloquean ambos `registro_importado` con `SELECT ... FOR UPDATE ORDER BY id`, y luego revalidan. Generar recibe `409` si algún extremo ya tiene conciliación `ACTIVE`. Confirmar primero lee sin lock los IDs inmutables de la pareja, bloquea ambos registros por ID ascendente, después bloquea la propuesta y revalida que siga `GENERATED`; entonces la cambia a `CONFIRMED`, crea la conciliación y deja que el trigger caduque las demás `GENERATED` incompatibles antes del commit. Este orden global es obligatorio para evitar deadlocks. Los estados terminales, la pareja y la evaluación son inmutables. La misma pareja solo se evalúa otra vez ante cambios relevantes de datos o de `rule_version`; no existe una acción pública para cambiar esa decisión terminal.

## Conciliaciones e historial

| Método y ruta | Entrada/filtros | Respuesta | Errores | RF |
|---|---|---|---|---|
| `GET /api/v1/reconciliations/{reconciliation_id}` | Path ID | `{id,status,proposal_id,movement,receipt,confirmed_by,confirmed_at,reversal?}` | 401, 404 | RF-10, RF-12 |
| `POST /api/v1/reconciliations/{reconciliation_id}/reverse` | JSON `{reason}` no vacío | `200 {id,status:"REVERSED",reversal:{reason,actor,occurred_at}}` | 401, 404, 409 ya revertida, 422 motivo | RF-12 |
| `GET /api/v1/history` | `target_type?,target_id?,event_type?,from?,to?,page,page_size` | Lista por `occurred_at DESC,id DESC` de `{id,event_type,target,actor?,reason?,data,occurred_at}` | 400, 401, 404 | RF-13 |

Revertir conserva conciliación y propuesta, libera ambos extremos y registra motivo, actor y fecha. No borra eventos. `history` puede reconstruir origen del lote, validaciones, generación, decisión y reversión.

## Normalización y ranking canónicos

`ref-nfkd-v1` aplica, exactamente en este orden: Unicode **NFKD**; eliminación de marcas combinantes; conversión a mayúsculas; cada signo de puntuación a espacio; colapso de espacios y `trim`; conjunto de tokens únicos. Conserva originales fuera de esta copia.

Jaccard es `|A ∩ B| / |A ∪ B|`; si la unión está vacía vale `0`. La igualdad exacta exige dos normalizados iguales **y no vacíos**; dos vacíos producen `false`. El desempate total es: igualdad exacta descendente, Jaccard descendente, diferencia absoluta de días ascendente, ID de movimiento ascendente e ID de comprobante ascendente.
