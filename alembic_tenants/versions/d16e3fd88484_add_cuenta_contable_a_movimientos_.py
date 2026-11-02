"""add_cuenta_contable_a_movimientos_bancarios

Revision ID: d16e3fd88484
Revises: 773774e0181a
Create Date: 2026-06-15 14:26:15.830608

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd16e3fd88484'
down_revision: Union[str, None] = '773774e0181a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"""
        ALTER TABLE {target_schema}.movimientos_bancarios
        ADD COLUMN IF NOT EXISTS cuenta_contable_id INTEGER;
    """)

    op.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_movimientos_bancarios_cuenta_contable'
                AND connamespace = '{target_schema}'::regnamespace
            ) THEN
                ALTER TABLE {target_schema}.movimientos_bancarios
                ADD CONSTRAINT fk_movimientos_bancarios_cuenta_contable
                FOREIGN KEY (cuenta_contable_id) REFERENCES {target_schema}.plan_cuentas (id);
            END IF;
        END
        $$;
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"""
        ALTER TABLE {target_schema}.movimientos_bancarios
        DROP CONSTRAINT IF EXISTS fk_movimientos_bancarios_cuenta_contable;
    """)

    op.execute(f"""
        ALTER TABLE {target_schema}.movimientos_bancarios
        DROP COLUMN IF EXISTS cuenta_contable_id;
    """)