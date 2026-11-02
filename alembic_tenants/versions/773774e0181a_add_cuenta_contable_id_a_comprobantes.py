"""add_cuenta_contable_id_a_comprobantes

Revision ID: 773774e0181a
Revises: 3d1e98a147c3
Create Date: 2026-06-15 14:00:19.523365

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '773774e0181a'
down_revision: Union[str, None] = '3d1e98a147c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 1. Agregamos la columna de forma segura
    op.execute(f"""
        ALTER TABLE {target_schema}.comprobantes
        ADD COLUMN IF NOT EXISTS cuenta_contable_id INTEGER;
    """)

    # 2. Agregamos la Foreign Key con un bloque DO para garantizar idempotencia,
    # ya que PostgreSQL no soporta "ADD CONSTRAINT IF NOT EXISTS" directamente.
    op.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_comprobantes_cuenta_contable'
                AND connamespace = '{target_schema}'::regnamespace
            ) THEN
                ALTER TABLE {target_schema}.comprobantes
                ADD CONSTRAINT fk_comprobantes_cuenta_contable
                FOREIGN KEY (cuenta_contable_id) REFERENCES {target_schema}.plan_cuentas (id);
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Reversión Defensiva: Primero eliminamos la restricción, luego la columna
    op.execute(f"""
        ALTER TABLE {target_schema}.comprobantes
        DROP CONSTRAINT IF EXISTS fk_comprobantes_cuenta_contable;
    """)

    op.execute(f"""
        ALTER TABLE {target_schema}.comprobantes
        DROP COLUMN IF EXISTS cuenta_contable_id;
    """)