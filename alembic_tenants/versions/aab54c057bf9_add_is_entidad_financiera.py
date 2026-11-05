"""add_is_entidad_financiera

Revision ID: aab54c057bf9
Revises: 7aa6de81a322
Create Date: 2026-07-18 21:45:26.121935

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aab54c057bf9'
down_revision: Union[str, None] = '7aa6de81a322'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Escudo de Idempotencia: ADD COLUMN IF NOT EXISTS
    op.execute(f"""
        ALTER TABLE {target_schema}.contactos_comerciales
        ADD COLUMN IF NOT EXISTS is_entidad_financiera BOOLEAN DEFAULT FALSE NOT NULL;
    """)


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Rollback Defensivo: DROP COLUMN IF EXISTS
    op.execute(f"""
        ALTER TABLE {target_schema}.contactos_comerciales
        DROP COLUMN IF EXISTS is_entidad_financiera;
    """)