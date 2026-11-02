"""fix_pk_padrones_fiscales

Revision ID: bd70411cf2c9
Revises: 771a4db4f9a8
Create Date: 2026-07-05 19:49:11.290733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd70411cf2c9'
down_revision: Union[str, None] = '771a4db4f9a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🌟 DDL Defensivo: Agrega columna, FK y reconstruye la Clave Primaria
    op.execute(f"""
        -- 1. Agregar columna de aislamiento
        ALTER TABLE {target_schema}.padrones_fiscales
        ADD COLUMN IF NOT EXISTS entidad_id INTEGER;

        DO $$
        BEGIN
            -- 2. Vincular Clave Foránea (Ignora si ya existe)
            IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'fk_padrones_fiscales_entidad' AND table_schema = '{target_schema}') THEN
                ALTER TABLE {target_schema}.padrones_fiscales
                ADD CONSTRAINT fk_padrones_fiscales_entidad FOREIGN KEY (entidad_id) REFERENCES {target_schema}.razones_sociales_propias(id) ON DELETE CASCADE;
            END IF;

            -- 3. Reconstrucción Segura de Primary Key
            -- Verifica si la PK actual ya tiene la columna entidad_id
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.key_column_usage
                WHERE table_schema = '{target_schema}' AND table_name = 'padrones_fiscales' AND column_name = 'entidad_id' AND constraint_name LIKE '%pkey'
            ) THEN
                ALTER TABLE {target_schema}.padrones_fiscales DROP CONSTRAINT IF EXISTS padrones_fiscales_pkey;
                ALTER TABLE {target_schema}.padrones_fiscales ADD PRIMARY KEY (entidad_id, cuit, jurisdiccion, periodo);
            END IF;
        END $$;
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🌟 Downgrade Defensivo: Reversión a la PK compuesta original
    op.execute(f"""
        ALTER TABLE {target_schema}.padrones_fiscales DROP CONSTRAINT IF EXISTS fk_padrones_fiscales_entidad;
        ALTER TABLE {target_schema}.padrones_fiscales DROP CONSTRAINT IF EXISTS padrones_fiscales_pkey;

        DO $$
        BEGIN
            -- Solo intenta recrear la PK anterior si las columnas base aún existen
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = '{target_schema}' AND table_name = 'padrones_fiscales' AND column_name = 'cuit') THEN
                ALTER TABLE {target_schema}.padrones_fiscales ADD PRIMARY KEY (cuit, jurisdiccion, periodo);
            END IF;
        END $$;

        ALTER TABLE {target_schema}.padrones_fiscales DROP COLUMN IF EXISTS entidad_id;
    """)