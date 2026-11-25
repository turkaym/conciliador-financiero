# Esquema PostgreSQL 16

`schema.sql` es el diseño físico ejecutable para una base PostgreSQL 16 vacía. Es una inicialización transaccional única y no idempotente; no presupone ejecuciones previas ni ofrece migraciones de aplicación.

## Inicialización local

1. Opcionalmente, defina `POSTGRES_DB`, `POSTGRES_USER` y `POSTGRES_PASSWORD`.
2. Ejecute `docker compose up --wait` desde la raíz con un **volumen nuevo**.
3. PostgreSQL ejecuta el montaje de solo lectura `/docker-entrypoint-initdb.d/001-schema.sql` únicamente al inicializar el directorio de datos.
4. Use `docker compose down -v` solo para el volumen descartable de este proyecto cuando necesite una inicialización limpia.

La contraseña predeterminada de Compose es solo local y no debe reutilizarse fuera de este entorno académico. `seed.sql` es idempotente: agrega o reactiva el usuario demo, mantiene fuentes/esquemas y actualiza funciones de integridad necesarias para bases existentes. Su contraseña local documentada es `Demo1234!`.

En un volumen existente, ejecute `app.initialize_database` con las variables de `.env` cargadas para aplicar nuevamente el seed; no es necesario destruir datos.

## Fuentes de verdad

- DDL físico: [`schema.sql`](schema.sql)
- Contrato por atributo: [`../docs/segunda-entrega/05-diccionario-de-datos.md`](../docs/segunda-entrega/05-diccionario-de-datos.md)
- Vistas conceptual y lógica: [`../docs/segunda-entrega/06-diagramas.md`](../docs/segunda-entrega/06-diagramas.md)
