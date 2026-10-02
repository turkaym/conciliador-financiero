# PostgreSQL 16 schema

`schema.sql` is the executable physical design for an empty PostgreSQL 16 database. It is a single transactional, non-idempotent initialization; it does not claim a prior execution or provide application migrations.

## Local initialization

1. Optionally set `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` in the shell.
2. Run `docker compose up --wait` from the repository root with a **new volume**.
3. PostgreSQL executes the read-only mount at `/docker-entrypoint-initdb.d/001-schema.sql` only when the data directory is first initialized.
4. Use `docker compose down -v` only for this project's disposable volume when a clean initialization is required.

The Compose default password is local-only and must not be reused outside this academic environment. The schema creates 12 tables, named constraints, query/uniqueness indexes, and seven integrity triggers. It does not seed users, catalogs, templates, or business data.

## Sources of truth

- Physical DDL: [`schema.sql`](schema.sql)
- Attribute-level contract: [`../docs/segunda-entrega/05-diccionario-de-datos.md`](../docs/segunda-entrega/05-diccionario-de-datos.md)
- Conceptual/logical views: [`../docs/segunda-entrega/06-diagramas.md`](../docs/segunda-entrega/06-diagramas.md)
