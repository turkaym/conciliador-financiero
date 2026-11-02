"""add_is_active_to_conciliacion_matches

Revision ID: e248eabed866
Revises: 30388acecac4
Create Date: 2026-06-16 15:05:10.929080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e248eabed866'
down_revision: Union[str, None] = '30388acecac4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Escudo de Idempotencia (SQL Crudo) para alterar la tabla existente
    op.execute(f"""
        ALTER TABLE "{target_schema}".conciliacion_matches
        ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL;
    """)


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Rollback Idempotente (Downgrade Defensivo)
    op.execute(f"""
        ALTER TABLE "{target_schema}".conciliacion_matches
        DROP COLUMN IF EXISTS is_active;
    """)