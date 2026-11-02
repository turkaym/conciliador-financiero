"""add_afip_vault_to_tenant

Revision ID: cd9a9ac758f1
Revises: b11af6c89fd6
Create Date: 2026-05-24 20:39:34.102356

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd9a9ac758f1'
down_revision: Union[str, None] = 'b11af6c89fd6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"""
        ALTER TABLE {target_schema}.razones_sociales_propias
        ADD COLUMN IF NOT EXISTS afip_certificate TEXT,
        ADD COLUMN IF NOT EXISTS afip_private_key_encrypted TEXT,
        ADD COLUMN IF NOT EXISTS afip_cert_expiration TIMESTAMP WITH TIME ZONE;
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"""
        ALTER TABLE {target_schema}.razones_sociales_propias
        DROP COLUMN IF EXISTS afip_certificate,
        DROP COLUMN IF EXISTS afip_private_key_encrypted,
        DROP COLUMN IF EXISTS afip_cert_expiration;
    """)