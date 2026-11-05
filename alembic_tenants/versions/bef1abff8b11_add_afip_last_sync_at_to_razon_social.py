"""add_afip_last_sync_at_to_razon_social

Revision ID: bef1abff8b11
Revises: bd70411cf2c9
Create Date: 2026-07-09 02:58:21.598537

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bef1abff8b11'
down_revision: Union[str, None] = 'bd70411cf2c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🌟 DDL Defensivo: Agregamos la columna de telemetría de forma idempotente
    op.execute(f"""
        ALTER TABLE {target_schema}.razones_sociales_propias
        ADD COLUMN IF NOT EXISTS afip_last_sync_at TIMESTAMP WITH TIME ZONE;
    """)


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🌟 DDL Defensivo: Eliminamos la columna de forma segura en caso de rollback
    op.execute(f"""
        ALTER TABLE {target_schema}.razones_sociales_propias
        DROP COLUMN IF EXISTS afip_last_sync_at;
    """)