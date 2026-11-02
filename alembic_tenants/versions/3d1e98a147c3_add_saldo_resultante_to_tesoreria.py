"""add_saldo_resultante_to_tesoreria

Revision ID: 3d1e98a147c3
Revises: cd05b35eaa2d
Create Date: 2026-06-11 14:09:54.523237

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d1e98a147c3'
down_revision: Union[str, None] = 'cd05b35eaa2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🛡️ ESCUDO DE IDEMPOTENCIA: Adición segura de columna (Numeric 18,2)
    op.execute(f"""
        ALTER TABLE {target_schema}.movimientos_tesoreria
        ADD COLUMN IF NOT EXISTS saldo_resultante NUMERIC(18, 2) DEFAULT 0.00 NOT NULL;
    """)


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🛡️ ROLLBACK DEFENSIVO: Eliminación silenciosa si la columna no existe
    op.execute(f"""
        ALTER TABLE {target_schema}.movimientos_tesoreria
        DROP COLUMN IF EXISTS saldo_resultante;
    """)