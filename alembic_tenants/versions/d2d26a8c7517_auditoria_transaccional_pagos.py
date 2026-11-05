"""auditoria_transaccional_pagos

Revision ID: d2d26a8c7517
Revises: a2f2c31f4b99
Create Date: 2026-05-31 20:00:27.572914

"""

from alembic import op
import sqlalchemy as sa

# ==========================================
# VARIABLES DE CONTROL DE ALEMBIC (OBLIGATORIAS)
# ==========================================
revision = 'd2d26a8c7517'
down_revision = 'a2f2c31f4b99'
branch_labels = None
depends_on = None

def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🌟 SQL Crudo Idempotente para añadir columnas de auditoría a las 3 tablas principales
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

    # 🌟 Reversión Idempotente
    op.execute(f"""
        ALTER TABLE {target_schema}.ordenes_pago DROP COLUMN IF EXISTS creado_por_id;
        ALTER TABLE {target_schema}.ordenes_pago DROP COLUMN IF EXISTS actualizado_por_id;

        ALTER TABLE {target_schema}.lotes_pago DROP COLUMN IF EXISTS creado_por_id;
        ALTER TABLE {target_schema}.lotes_pago DROP COLUMN IF EXISTS actualizado_por_id;

        ALTER TABLE {target_schema}.lote_pago_detalles DROP COLUMN IF EXISTS creado_por_id;
        ALTER TABLE {target_schema}.lote_pago_detalles DROP COLUMN IF EXISTS actualizado_por_id;
    """)