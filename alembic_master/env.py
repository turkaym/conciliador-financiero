import os
import sys
from logging.config import fileConfig
from sqlalchemy import text
from alembic import context

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core.database.base import Base as MasterBase
import core.database.models_master
import core.database.models.sistema
from core.database.session import engine as app_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = MasterBase.metadata

def run_migrations_online():
    with app_engine.connect() as connection:
        # Abre transacción implícita
        connection.execute(text("SET search_path TO public"))
        # CORRECCIÓN CRÍTICA: Forzamos el commit para que Alembic recupere el control del ciclo de vida
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="alembic_version_master",
            include_schemas=False
        )
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()