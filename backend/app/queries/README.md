# Consultas

- **Propósito:** ofrecer vistas paginadas de pendientes, lotes, propuestas, conciliaciones, errores e historial.
- **Entrada:** filtros autenticados, página y tamaño.
- **Salida:** modelos de lectura estables con procedencia y estado.
- **RF:** RF-07, RF-13; RNF-06.
- **Dependencias:** interfaces de consulta de solo lectura.
- **Exclusiones:** cambios de dominio y propiedad directa de tablas.
# Pending Queries

`GET /api/v1/pending` returns owner-scoped, genuinely unreconciled records. Results
are ordered by `created_at ASC, record_id ASC` and use one-based pagination.

Supported filters are `type`, `source_id`, `batch_id`, `state`, `from`, and `to`.
`from` and `to` filter the transaction date inclusively. The endpoint excludes
invalid records and records linked to an active reconciliation; it does not create,
update, or score proposals.
