# Esquema PostgreSQL 16

`schema.sql` es el diseño físico ejecutable para una base PostgreSQL 16 vacía. Es una inicialización transaccional única y no idempotente; no presupone ejecuciones previas ni ofrece migraciones de aplicación.

## Inicialización local

1. Opcionalmente, defina `POSTGRES_DB`, `POSTGRES_USER` y `POSTGRES_PASSWORD`.
2. Ejecute `docker compose up --wait` desde la raíz con un **volumen nuevo**.
3. PostgreSQL ejecuta el montaje de solo lectura `/docker-entrypoint-initdb.d/001-schema.sql` únicamente al inicializar el directorio de datos.
4. Use `docker compose down -v` solo para el volumen descartable de este proyecto cuando necesite una inicialización limpia.

La contraseña predeterminada de Compose es solo local y no debe reutilizarse fuera de este entorno académico. El esquema crea **12 tablas, 106 columnas, 109 constraints, 52 índices y 8 triggers** de integridad. No carga usuarios, catálogos, plantillas ni datos de negocio.

## Fuentes de verdad

- DDL físico: [`schema.sql`](schema.sql)
- Contrato por atributo: [`../docs/segunda-entrega/05-diccionario-de-datos.md`](../docs/segunda-entrega/05-diccionario-de-datos.md)
- Vistas conceptual y lógica: [`../docs/segunda-entrega/06-diagramas.md`](../docs/segunda-entrega/06-diagramas.md)
