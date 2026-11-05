import os
import sys
import logging
from sqlalchemy import create_engine, text
from alembic import context

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core.database.models_tenant import TenantBase
from core.database.session import engine as app_engine

logger = logging.getLogger("alembic.env")
config = context.config

target_metadata = TenantBase.metadata

def include_object(object, name, type_, reflected, compare_to):
    if getattr(object, "schema", None) == "public":
        return False
    if type_ == "table" and name == "alembic_version":
        return False
    if type_ in ("unique_constraint", "index"):
        table_name = getattr(object, "table", None)
        if table_name is not None and getattr(table_name, "schema", None) == "public":
            return False
        if table_name is not None and table_name.name == "secuencias_fiscales":
            return False
        if name and "tenant_template" in name:
            return False
    return True

def run_migrations_online():
    logger.info("🟢 [ALEMBIC ENV] Iniciando entorno de migraciones...")
    is_revision_mode = any(arg in sys.argv for arg in ['revision', 'autogenerate'])

    x_args = context.get_x_argument(as_dictionary=True)
    specific_tenant = config.attributes.get('tenant_schema') or x_args.get('tenant_schema')
    injected_connection = config.attributes.get('connection')

    try:
        if injected_connection:
            logger.info("✅ [ALEMBIC ENV] Usando conexión inyectada segura. Ejecutando DDL...")
            connection = injected_connection
        else:
            logger.info("🔧 [ALEMBIC ENV] Usando app_engine (PgBouncer)")
            connection = app_engine.connect()

        if is_revision_mode:
            target_schema = "tenant_template"
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS tenant_template"))
            connection.commit()

            connection.execute(text(f'SET search_path TO "{target_schema}", public'))
            connection.commit()

            connection.dialect.default_schema_name = target_schema

            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                version_table="alembic_version",
                version_table_schema=target_schema,
                include_schemas=False,
                include_object=include_object
            )
            with context.begin_transaction():
                context.run_migrations()

            connection.commit()

        elif specific_tenant:
            # En la versión inyectada, el context.connect() ya tiene el schema pre-configurado
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                version_table="alembic_version",
                version_table_schema=specific_tenant,
                include_object=include_object
            )
            with context.begin_transaction():
                context.run_migrations()

            logger.info("🏁 [ALEMBIC ENV] Migraciones finalizadas con éxito.")
        else:
            logger.error("[ERROR DE ARQUITECTURA] No se especificó el esquema de destino.")
            raise RuntimeError("Ejecución de Alembic abortada: Falta el parámetro de esquema de destino.")
    finally:
        if not injected_connection and 'connection' in locals():
            connection.close()

run_migrations_online()