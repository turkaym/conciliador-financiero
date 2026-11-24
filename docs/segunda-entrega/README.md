# Second delivery: pre-coding design

This package defines CONCILIADOR's functional scope, rules, data, and target architecture. Product coding and discovery had not started when these academic documents were created. The modular READMEs, CSV, SVG, Compose, and SQL files are documentation assets; they do not constitute an implemented application.

## Recommended review path

1. [Scope and modules](01-alcance-y-modulos.md)
2. [Requirements](02-requerimientos.md) and [business rules](03-reglas-de-negocio.md)
3. [Database design](04-diseno-base-de-datos.md) and [data dictionary](05-diccionario-de-datos.md)
4. [Diagrams](06-diagramas.md)
5. [Decisions and assumptions](07-decisiones-y-supuestos.md)
6. [API contract](09-contrato-api.md), [CSV](csv/README.md), and [wireframes](wireframes/README.md)
7. [Traceability matrix](08-matriz-trazabilidad.md)

The [glossary](glosario.md) defines the common vocabulary. The requirements, rules, and dictionary documents are the canonical sources for their respective details; the others link to them without duplicating them.

## Delivery boundaries

- The academic MVP is documented before coding it.
- Discovery is **Not started** and coding is **Not started** in this pre-coding package; no interviews or prior executions are attributed to it.
- Timing from a future test will be an observation, not a service commitment.
- The eight Mermaid sources are integrated into the diagrams document so GitHub renders them without duplicate files.
- The documented local environment contains only PostgreSQL 16; the backend/frontend skeletons are READMEs only.
