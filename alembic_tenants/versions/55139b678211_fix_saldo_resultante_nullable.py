"""fix_saldo_resultante_nullable

Revision ID: 55139b678211
Revises: 014020e208f4
Create Date: 2026-07-18 03:40:16.760803

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55139b678211'
down_revision: Union[str, None] = '014020e208f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🌟 DDL Defensivo: Permitimos NULL y quitamos el default
    op.execute(f"""
        ALTER TABLE {target_schema}.movimientos_tesoreria
        ALTER COLUMN saldo_resultante DROP NOT NULL,
        ALTER COLUMN saldo_resultante DROP DEFAULT;
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🌟 Rollback Idempotente: Primero parcheamos posibles nulos para que el SET NOT NULL no colapse
    op.execute(f"""
        UPDATE {target_schema}.movimientos_tesoreria
        SET saldo_resultante = 0.00
        WHERE saldo_resultante IS NULL;

        ALTER TABLE {target_schema}.movimientos_tesoreria
        ALTER COLUMN saldo_resultante SET DEFAULT '0.00',
        ALTER COLUMN saldo_resultante SET NOT NULL;
    """)