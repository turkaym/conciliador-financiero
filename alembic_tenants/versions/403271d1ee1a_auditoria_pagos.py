"""auditoria_pagos

Revision ID: 403271d1ee1a
Revises: d2d26a8c7517
Create Date: 2026-05-31 20:16:13.125485

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# 🌟 FIX: Identificadores de revisión obligatorios para Alembic
revision: str = '403271d1ee1a'
down_revision: Union[str, None] = 'd2d26a8c7517'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"""
        ALTER TABLE {target_schema}.ordenes_pago
        ADD COLUMN IF NOT EXISTS creado_por_id VARCHAR(50),
        ADD COLUMN IF NOT EXISTS actualizado_por_id VARCHAR(50);

        ALTER TABLE {target_schema}.lotes_pago
        ADD COLUMN IF NOT EXISTS creado_por_id VARCHAR(50),
        ADD COLUMN IF NOT EXISTS actualizado_por_id VARCHAR(50);

        ALTER TABLE {target_schema}.lote_pago_detalles
        ADD COLUMN IF NOT EXISTS creado_por_id VARCHAR(50),
        ADD COLUMN IF NOT EXISTS actualizado_por_id VARCHAR(50);
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"""
        ALTER TABLE {target_schema}.ordenes_pago DROP COLUMN IF EXISTS creado_por_id;
        ALTER TABLE {target_schema}.ordenes_pago DROP COLUMN IF EXISTS actualizado_por_id;
        ALTER TABLE {target_schema}.lotes_pago DROP COLUMN IF EXISTS creado_por_id;
        ALTER TABLE {target_schema}.lotes_pago DROP COLUMN IF EXISTS actualizado_por_id;
        ALTER TABLE {target_schema}.lote_pago_detalles DROP COLUMN IF EXISTS creado_por_id;
        ALTER TABLE {target_schema}.lote_pago_detalles DROP COLUMN IF EXISTS actualizado_por_id;
    """)