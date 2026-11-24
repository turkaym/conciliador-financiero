import os
from pathlib import Path

import psycopg

from app.config import settings


def _database_url_for_psycopg() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def initialize_database() -> None:
    schema_path = Path(os.getenv("DATABASE_SCHEMA_PATH", "database/schema.sql"))
    seed_path = Path(os.getenv("DATABASE_SEED_PATH", "database/seed.sql"))

    with psycopg.connect(_database_url_for_psycopg()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext('conciliador-init'))")
            cursor.execute("SELECT to_regclass('public.usuario')")
            schema_exists = cursor.fetchone()[0] is not None
            if not schema_exists:
                cursor.execute(schema_path.read_text(encoding="utf-8"))
            cursor.execute(seed_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    initialize_database()
