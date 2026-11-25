# Módulos de aplicación

Las carpetas contienen la implementación del monolito modular:

| Módulo | Función |
|---|---|
| `access` | Autenticación e identidad. |
| `import_catalogs` | Fuentes, esquemas y columnas. |
| `imports` | Ciclo de lote y deduplicación. |
| `validation` | Parseo, mapeo y normalización. |
| `queries` | Consolidado y lecturas operativas. |
| `proposals` | Generación, sincronización y ranking. |
| `reconciliation` | Decisiones, manual, auditoría, exportación y reversión. |
| `audit` | Historial append-only. |

Las reglas críticas se ejecutan en servicios transaccionales y PostgreSQL agrega restricciones/triggers de respaldo.
