"""add_saldo_retenido_to_cuentas

Revision ID: c0dc4d038402
Revises: 48c2b2a11727
Create Date: 2026-05-10 21:08:13.832868

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0dc4d038402'
down_revision: Union[str, None] = '48c2b2a11727'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Inyección Idempotente SQL
    op.execute(f"""
        ALTER TABLE {target_schema}.cuentas_bancarias
        ADD COLUMN IF NOT EXISTS saldo_retenido NUMERIC(18, 2) DEFAULT 0.00 NOT NULL;
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Downgrade Defensivo
    op.execute(f"""
        ALTER TABLE {target_schema}.cuentas_bancarias
        DROP COLUMN IF EXISTS saldo_retenido;
    """)