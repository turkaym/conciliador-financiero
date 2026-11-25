# Segunda entrega - documentación vigente

Este paquete comenzó como diseño previo a la codificación y fue actualizado para reflejar el MVP implementado. Los documentos canónicos son:

1. [Alcance y módulos](01-alcance-y-modulos.md)
2. [Requerimientos](02-requerimientos.md)
3. [Reglas de negocio](03-reglas-de-negocio.md)
4. [Diseño de base de datos](04-diseno-base-de-datos.md)
5. [Diccionario de datos](05-diccionario-de-datos.md)
6. [Diagramas](06-diagramas.md)
7. [Decisiones y supuestos](07-decisiones-y-supuestos.md)
8. [Matriz de trazabilidad](08-matriz-trazabilidad.md)
9. [Contrato API](09-contrato-api.md)
10. [CSV y casos de prueba](csv/README.md)

## Estado

- Backend FastAPI, frontend React y esquema PostgreSQL implementados.
- Importación por fuente, deduplicación, consolidado, conciliación automática/manual, auditoría, reversión y exportación disponibles.
- El módulo visual Pendientes fue reemplazado por Consolidado y Propuestas > Manual.
- La documentación de datos y diagramas conserva el diseño físico original; ante diferencias operativas, `database/schema.sql`, `database/seed.sql` y el contrato API vigente son la referencia ejecutable.
- La última validación local registró 44 pruebas backend, 17 frontend y build aprobado.

La aplicación es académica, utiliza datos ficticios y no debe procesar información financiera real.
