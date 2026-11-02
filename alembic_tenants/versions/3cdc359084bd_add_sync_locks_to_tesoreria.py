"""add_sync_locks_to_tesoreria

Revision ID: 3cdc359084bd
Revises: bef1abff8b11
Create Date: 2026-07-10 23:32:38.971558

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3cdc359084bd'
down_revision: Union[str, None] = 'bef1abff8b11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # DDL Defensivo: Inyección segura de candados de concurrencia
    op.execute(f"""
        ALTER TABLE {target_schema}.cuentas_tesoreria
        ADD COLUMN IF NOT EXISTS is_syncing BOOLEAN DEFAULT FALSE NOT NULL,
        ADD COLUMN IF NOT EXISTS last_task_id VARCHAR(255);
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Rollback Idempotente
    op.execute(f"""
        ALTER TABLE {target_schema}.cuentas_tesoreria
        DROP COLUMN IF EXISTS is_syncing,
        DROP COLUMN IF EXISTS last_task_id;
    """)