# HTTP Contract `/api/v1`

Pre-coding contract for the modular monolith. All operations except login require authentication. JSON uses UTF-8, `snake_case` names, `YYYY-MM-DD` business dates, and RFC 3339 UTC timestamps. IDs are positive integers and amounts are serialized as decimal strings.

## Conventions

Lists respond with `{ "page": 1, "page_size": 25, "total": 0, "items": [] }`. `page >= 1`; `page_size` accepts `1..100` and defaults to `25`. Stable ordering uses the declared criterion followed by `id ASC`.

The API model translates physical names without changing their meaning: `normalizador_version` -> `normalizer_version`, `version_regla` -> `rule_version`, `score_referencia` -> `reference_score`, `coincidencia_exacta` -> `exact_match`, `diferencia_dias` -> `day_difference`, and `explicacion` -> `ranking`.

Errors use:

```json
{"code":"CODIGO_ESTABLE","message":"Explanation","field":"optional_field","details":{},"trace_id":"uuid"}
```

| HTTP | Uso |
|---:|---|
| 400 | Malformed request, multipart body, or parameter. |
| 401 | Missing or invalid credential. |
| 404 | Resource does not exist or is not visible. |
| 409 | Incompatible state, duplicate, or concurrency condition. |
| 422 | Domain rule or semantically invalid field. |
| 500 | Unexpected failure; `trace_id` enables correlation without exposing secrets. |

## Access and catalogs

| Method and path | Input | Response | Errors | RF |
|---|---|---|---|---|
| `POST /api/v1/auth/login` | JSON `{email,password}` | `200 {access_token,token_type:"bearer",expires_in,user:{id,email}}` | 400, 401, 422 | RF-01 |
| `GET /api/v1/catalog/sources` | Query `type?=MOVIMIENTO\|COMPROBANTE` | Active list `{id,code,name,type}` | 400, 401 | RF-02 |
| `GET /api/v1/catalog/templates` | Query `source_id,type` | Compatible list `{id,name,type,version,columns[]}` | 400, 401, 404 | RF-02 |

Login never reveals whether an email exists. Token handling and storage are implementation details; the contract does not expose hashes.

## Batches, errors, and pending records

### Create batch

`POST /api/v1/batches` receives `multipart/form-data`: `source_id` (ID), `template_id` (exact catalog ID), `type` (`MOVIMIENTO|COMPROBANTE`), and `file` (one CSV). Name and version are informational in `GET /catalog/templates`; selection and resolution use only `template_id`. It responds with `202`:

```json
{"id":31,"status":"PROCESADO_CON_ERRORES","requested_template_id":17,"template":{"id":17,"name":"bank","version":1},"file_name":"movimientos.csv","received_at":"2026-05-01T12:00:00Z"}
```

The implementation may respond after synchronous processing completes while retaining `202`. A recognized structure processed with zero valid rows returns `PROCESADO_SIN_VALIDOS`; a mixed result uses `PROCESADO_CON_ERRORES`; a fully valid result uses `PROCESADO`. An unknown template, uninterpretable structure, or technical failure uses `FALLIDO` with `UNKNOWN_TEMPLATE`, `INVALID_FILE_STRUCTURE`, or `PROCESSING_FAILED`, without processed rows. `FALLIDO` preserves the attempt/error but does not reserve the fingerprint, so the same bytes can be submitted again. A reservation conflict directly creates terminal `DUPLICADO` with `original_batch_id`, an event, and zero rows. If the concurrent owner fails, the duplicate is not promoted and another submission is required. HTTP errors: 400 unreadable multipart, 401, 404 source, 409 conflict, 422 type/file.

| Method and path | Input/filters | Response | Errors | RF |
|---|---|---|---|---|
| `GET /api/v1/batches/{batch_id}` | Path ID | `{id,source,template?:{id,name,version},requested_template_id,type,file_name,status,totals,original_batch_id?,received_at,finished_at?}` | 401, 404 | RF-02, RF-03, RF-06 |
| `GET /api/v1/batches/{batch_id}/errors` | `page,page_size,scope?,field?` | Lista de `{id,scope,row_number?,field?,code,message,original_record_id?,created_at}` | 400, 401, 404 | RF-03, RF-06 |
| `GET /api/v1/pending` | `type?,batch_id?,state?,page,page_size` | List ordered by `created_at,id` of `{record_id,type,batch_id,external_id?,date,amount,currency,reference_original,state,cause}` | 400, 401, 404 | RF-07 |

The current implementation returns the Spanish status values used by the API and UI, including `PROCESADO`, `PROCESADO_CON_ERRORES`, `PROCESADO_SIN_VALIDOS`, `FALLIDO`, and `DUPLICADO`. These values map 1:1 to the documented SQL states; the response never translates or modifies the original implementation values.

## Proposals

Proposals are generated automatically when a batch ends in `PROCESADO` or `PROCESADO_CON_ERRORES`, and during a reversal. Each eligible record is compared with historical opposite pending records. `PROCESADO_SIN_VALIDOS`, `FALLIDO`, and `DUPLICADO` do not trigger matching.

`GET /api/v1/proposals` accepts `status?`, `batch_id?`, `page`, and `page_size`; it orders by `exact_match DESC`, `reference_score DESC`, `absolute_day_difference ASC`, `movement_id ASC`, and `receipt_id ASC`. It returns summarized items with IDs, dates, amounts, status, score, and versions. RF-08, RF-09.

`GET /api/v1/proposals/{proposal_id}` devuelve:

```json
{
  "id": 81,
"status": "GENERADA",
  "evaluation_fingerprint": "sha256:base64url",
  "movement": {"record_id": 11, "batch_id": 3, "date": "2026-04-10", "amount": "1500.00", "currency": "ARS", "reference_original": "FACTURA 100"},
  "receipt": {"record_id": 24, "batch_id": 7, "date": "2026-04-11", "amount": "1500.00", "currency": "ARS", "reference_original": "Factura-100"},
  "ranking": {"exact_match": true, "reference_score": "1.0000", "day_difference": 1, "normalizer_version": "ref-nfkd-v1", "rule_version": "match-v1", "movement_normalized": "FACTURA 100", "receipt_normalized": "FACTURA 100", "movement_tokens": ["100","FACTURA"], "receipt_tokens": ["100","FACTURA"]},
  "origin": {"type": "BATCH", "batch_id": 7, "reverted_reconciliation_id": null, "generated_at": "2026-04-24T10:00:00Z"},
  "decision": null
}
```

Errors: 401, 404. The reference explains and ranks; ARS, exact amount, and a date within ±3 days determine eligibility.

### Decisions

| Method and path | Input | Response | Errors | RF |
|---|---|---|---|---|
| `POST /api/v1/proposals/{proposal_id}/confirm` | Empty JSON `{}` | `200 {proposal:{id,status:"CONFIRMADA",decided_by,decided_at},reconciliation:{id,status:"ACTIVA"}}` | 401, 404, 409 state/race, 422 ineligible | RF-10 |
| `POST /api/v1/proposals/{proposal_id}/reject` | Non-empty JSON `{reason}` | `200 {id,status:"RECHAZADA",reason,decided_by,decided_at}` | 401, 404, 409 terminal, 422 reason | RF-11 |

Generation and confirmation share a protocol: they lock records with `SELECT ... FOR UPDATE ORDER BY id` and revalidate. Confirmation first reads immutable IDs, locks records, then the proposal, changes it to `CONFIRMADA`, creates the reconciliation, and expires incompatible proposals. Pair, evaluation, origin, and terminal values are immutable. Pair + `rule_version` + `evaluation_fingerprint` suppresses an identical rejection; new data or rules allow another evaluation, never reopening a terminal record.

## Reconciliations and history

| Method and path | Input/filters | Response | Errors | RF |
|---|---|---|---|---|
| `GET /api/v1/reconciliations/{reconciliation_id}` | Path ID | `{id,status,proposal_id,movement,receipt,confirmed_by,confirmed_at,reversal?}` | 401, 404 | RF-10, RF-12 |
| `POST /api/v1/reconciliations/{reconciliation_id}/reverse` | Non-empty JSON `{reason}` | `200 {id,status:"REVERTIDA",reversal:{reason,actor,occurred_at},generated_proposals:[{id,origin:{type:"REVERSAL",reverted_reconciliation_id}}]}` | 401, 404, 409 repetition/race, 422 reason | RF-12 |
| `GET /api/v1/history` | `target_type?,target_id?,event_type?,from?,to?,page,page_size` | List ordered by `occurred_at DESC,id DESC` of `{id,event_type,target,actor?,reason?,data,occurred_at}` | 400, 401, 404 | RF-13 |

Reversal reads immutable IDs, gathers candidates, and globally locks all `registro_importado` rows by `id ASC`; it then locks the reconciliation and revalidates `ACTIVA`. In one transaction it marks it `REVERTIDA`, releases both endpoints, rematches immediately, skips rejections and the recently reversed pair with identical data/rule, creates new proposals with `REVERSION` origin, and adds audit data. A relevant change or new `rule_version` allows that pair to reappear. Any error rolls back the whole operation; terminal states do not change.

## Canonical normalization and ranking

`ref-nfkd-v1` applies, exactly in this order: Unicode **NFKD**; removal of combining marks; uppercase conversion; each punctuation mark becomes a space; whitespace collapse and `trim`; unique token set. Originals are preserved outside this copy.

Jaccard is `|A ∩ B| / |A ∪ B|`; an empty union is `0`. Exact equality requires two equal **and non-empty** normalized values; two empty values produce `false`. The complete tie-break order is: exact match descending, Jaccard descending, absolute day difference ascending, movement ID ascending, and receipt ID ascending.
