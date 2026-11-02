"""migrar_comprobante_numero_a_bigint

Revision ID: 09e89e721f64
Revises: 75a78d202cd7
Create Date: 2026-07-18 02:22:24.066917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09e89e721f64'
down_revision: Union[str, None] = '75a78d202cd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Modificamos el tipo de dato físico a BIGINT (64-bits)
    op.execute(f"""
        ALTER TABLE {target_schema}.comprobantes
        ALTER COLUMN numero TYPE BIGINT;
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Downgrade defensivo a Integer
    op.execute(f"""
        ALTER TABLE {target_schema}.comprobantes
        ALTER COLUMN numero TYPE INTEGER;
    """)