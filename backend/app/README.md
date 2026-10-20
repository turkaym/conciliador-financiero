# Módulos de aplicación

Estas carpetas, formadas solo por README, dividen el monolito previsto por responsabilidad; no afirman implementación.

| Módulo | Propósito | RF principales |
|---|---|---|
| [`access`](access/README.md) | Autenticación e identidad del actor | RF-01 |
| [`import_catalogs`](import_catalogs/README.md) | Fuentes y plantillas | RF-02 |
| [`imports`](imports/README.md) | Recepción y deduplicación de lotes | RF-02, RF-06 |
| [`validation`](validation/README.md) | Validación y normalización de filas | RF-03–RF-05 |
| [`proposals`](proposals/README.md) | Generación y ranking automáticos | RF-08, RF-09 |
| [`reconciliation`](reconciliation/README.md) | Decisiones humanas y reversión | RF-10–RF-12 |
| [`queries`](queries/README.md) | Consultas de pendientes e historial | RF-07, RF-13 |
| [`audit`](audit/README.md) | Atribución append-only de eventos | RF-13 |
