# Contrato HTTP `/api/v1`

Salvo login, todas las rutas requieren `Authorization: Bearer <token>`. Fechas de negocio usan `YYYY-MM-DD`, timestamps RFC 3339 y montos cadenas decimales.

Errores:

```json
{"code":"CODIGO","message":"Descripción","details":{},"trace_id":"uuid"}
```

## Acceso y catálogos

| Método | Ruta | Uso |
|---|---|---|
| POST | `/auth/login` | `{email,password}` → token y usuario. |
| GET | `/catalog/sources?type=` | Bancos o entidades activas. |
| GET | `/catalog/templates?source_id=&type=` | Esquema compatible y columnas esperadas. |

La UI usa el único esquema activo y no presenta selector de plantilla.

## Importación

| Método | Ruta | Uso |
|---|---|---|
| POST | `/batches` | Multipart: `source_id`, `template_id` resuelto, `type`, `file`. |
| GET | `/batches/{id}` | Estado, fuente, esquema, totales y fechas. |
| GET | `/batches/{id}/errors` | Errores paginados por lote. |

El backend acepta delimitadores soportados y mapea columnas de origen a campos canónicos. Un lote mixto continúa procesando filas válidas.

## Consolidado

`GET /records` requiere `type=MOVIMIENTO|COMPROBANTE` y admite:

- `source_id`, `batch_id`, `reconciled`.
- `amount`, `amount_tolerance`, `reference`.
- `from`, `to`.
- `sort_by`, `sort_order`, `page`, `page_size`.

Devuelve fuente, lote, fecha, monto, moneda, descripción, estado y bandera conciliada.

`GET /pending` permanece como endpoint técnico compatible, pero no tiene pantalla propia.

## Propuestas

| Método | Ruta | Uso |
|---|---|---|
| POST | `/proposals/sync` | Reevalúa registros libres. Responde `{generated_count,proposal_ids}`. |
| GET | `/proposals?status=&batch_id=` | Lista ordenada de propuestas. |
| GET | `/proposals/{id}` | Pareja, ranking, versiones, huella, origen y decisión. |
| POST | `/proposals/{id}/confirm` | Confirma y crea conciliación activa. |
| POST | `/proposals/{id}/reject` | Requiere `{reason}`. |

`POST /proposals/sync` es idempotente respecto de propuestas `GENERADA` y rechazos idénticos. Una propuesta que comparte registros con otra confirmada puede quedar `CADUCADA`; confirmar una obsoleta responde 409.

## Conciliaciones

| Método | Ruta | Uso |
|---|---|---|
| POST | `/reconciliations/manual` | `{movement_id,receipt_id}`. |
| GET | `/reconciliations` | Auditoría paginada; por defecto `status=ACTIVA`. |
| GET | `/reconciliations/{id}` | Detalle histórico. |
| POST | `/reconciliations/{id}/reverse` | Requiere `{reason}`. |
| GET | `/reconciliations/export.csv` | Exporta activas filtradas. |

Filtros compartidos de Auditoría/exportación:

- `confirmed_from`, `confirmed_to`.
- `movement_from`, `movement_to`.
- `receipt_from`, `receipt_to`.
- `movement_source_id`, `receipt_source_id`.
- `amount`, `reference`, `batch_id`.
- `origin=AUTOMATICA|MANUAL`.

La exportación contiene `conciliacion_id`, fecha, origen, usuario, lado, cuenta, fecha de operación, referencia, lote, Debe, Haber y diferencia.

## Historial

`GET /history` admite objetivo, evento y fechas, y devuelve actor, motivo, datos y timestamp.

## Códigos relevantes

| HTTP | Ejemplos |
|---:|---|
| 400 | Parámetros o ventanas inválidas. |
| 401 | Token ausente/inválido. |
| 404 | Recurso inexistente o de otro usuario. |
| 409 | Propuesta decidida, registro conciliado, reversión repetida o carrera. |
| 422 | Motivo vacío o par manual inválido. |
| 500 | Error inesperado con `trace_id`; no debe usarse para conflictos esperados. |
