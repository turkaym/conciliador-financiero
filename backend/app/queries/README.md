# Consultas

`GET /api/v1/records` alimenta Consolidado y la selección manual. Soporta tipo, fuente, lote, conciliado, fechas, monto/tolerancia, referencia, orden y paginación.

`GET /api/v1/pending` se conserva como endpoint técnico compatible para registros `PENDIENTE|CON_PROPUESTAS`, pero no tiene módulo frontend. La experiencia vigente usa Consolidado con `reconciled=false`.

Todas las consultas se limitan al usuario autenticado y excluyen filas inválidas cuando corresponde.
