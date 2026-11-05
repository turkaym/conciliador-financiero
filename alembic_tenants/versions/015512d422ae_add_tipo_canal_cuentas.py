"""add_tipo_canal_cuentas

Revision ID: 015512d422ae
Revises: aab54c057bf9
Create Date: 2026-07-18 22:07:56.202174

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '015512d422ae'
down_revision: Union[str, None] = 'aab54c057bf9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"""
        ALTER TABLE {target_schema}.cuentas_bancarias
        ADD COLUMN IF NOT EXISTS tipo_canal VARCHAR(50) DEFAULT 'BANCO' NOT NULL,
        ADD COLUMN IF NOT EXISTS is_virtual_clearing BOOLEAN DEFAULT FALSE NOT NULL;
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"""
        ALTER TABLE {target_schema}.cuentas_bancarias
        DROP COLUMN IF EXISTS tipo_canal,
        DROP COLUMN IF EXISTS is_virtual_clearing;
    """)