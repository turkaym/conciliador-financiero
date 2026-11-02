import enum

"""fase_11_motor_fiscal

Revision ID: 195729d72bfa
Revises: 403271d1ee1a
Create Date: 2026-06-03 16:31:36.771287

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '195729d72bfa'
down_revision: Union[str, None] = '403271d1ee1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 1. Inyección de Condición Fiscal (Razones Sociales y Contactos)
    op.execute(f"""
        ALTER TABLE {target_schema}.razones_sociales_propias
        ADD COLUMN IF NOT EXISTS condicion_fiscal VARCHAR(50) DEFAULT 'NO_CATEGORIZADO' NOT NULL;
    """)

    op.execute(f"""
        ALTER TABLE {target_schema}.contactos_comerciales
        ADD COLUMN IF NOT EXISTS condicion_fiscal VARCHAR(50) DEFAULT 'NO_CATEGORIZADO' NOT NULL;
    """)

    # 2. Desglose Estructural Híbrido en Comprobantes (Columnas JSONB y Numeric)
    op.execute(f"""
        ALTER TABLE {target_schema}.comprobantes
        ADD COLUMN IF NOT EXISTS importe_neto_gravado NUMERIC(18, 2) DEFAULT 0.0,
        ADD COLUMN IF NOT EXISTS importe_no_gravado NUMERIC(18, 2) DEFAULT 0.0,
        ADD COLUMN IF NOT EXISTS importe_exento NUMERIC(18, 2) DEFAULT 0.0,
        ADD COLUMN IF NOT EXISTS subtotales_iva JSONB,
        ADD COLUMN IF NOT EXISTS otros_tributos JSONB,
        ADD COLUMN IF NOT EXISTS legacy_fiscal_data BOOLEAN DEFAULT FALSE NOT NULL;
    """)

    # 3. Índices GIN de Alta Velocidad (Tolerante a fallos si ya existen)
    op.execute(f"""
        CREATE INDEX IF NOT EXISTS ix_comprobantes_iva_gin
        ON {target_schema}.comprobantes USING gin (subtotales_iva);
    """)
    op.execute(f"""
        CREATE INDEX IF NOT EXISTS ix_comprobantes_tributos_gin
        ON {target_schema}.comprobantes USING gin (otros_tributos);
    """)


def downgrade() -> None:
    # ROLLBACK IDEMPOTENTE: Jamás asumimos que el objeto existe.
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Destrucción de Índices
    op.execute(f"DROP INDEX IF EXISTS {target_schema}.ix_comprobantes_tributos_gin;")
    op.execute(f"DROP INDEX IF EXISTS {target_schema}.ix_comprobantes_iva_gin;")

    # Destrucción de Columnas (Cascada segura IF EXISTS)
    op.execute(f"""
        ALTER TABLE {target_schema}.comprobantes
        DROP COLUMN IF EXISTS importe_neto_gravado,
        DROP COLUMN IF EXISTS importe_no_gravado,
        DROP COLUMN IF EXISTS importe_exento,
        DROP COLUMN IF EXISTS subtotales_iva,
        DROP COLUMN IF EXISTS otros_tributos,
        DROP COLUMN IF EXISTS legacy_fiscal_data;
    """)

    op.execute(f"ALTER TABLE {target_schema}.contactos_comerciales DROP COLUMN IF EXISTS condicion_fiscal;")
    op.execute(f"ALTER TABLE {target_schema}.razones_sociales_propias DROP COLUMN IF EXISTS condicion_fiscal;")