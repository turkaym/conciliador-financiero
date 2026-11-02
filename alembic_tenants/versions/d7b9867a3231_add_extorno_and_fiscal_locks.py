"""add_extorno_and_fiscal_locks

Revision ID: d7b9867a3231
Revises: e9b16cfb8849
Create Date: 2026-08-05 00:29:29.871281

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7b9867a3231'
down_revision: Union[str, None] = 'e9b16cfb8849'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 1. Escudo Idempotente: Columnas de Extorno en Asientos Contables
    op.execute(f"""
        ALTER TABLE {target_schema}.asientos_contables
        ADD COLUMN IF NOT EXISTS estado VARCHAR DEFAULT 'VIGENTE' NOT NULL,
        ADD COLUMN IF NOT EXISTS asiento_revertido_id INTEGER,
        ADD CONSTRAINT fk_asientos_revertido
        FOREIGN KEY (asiento_revertido_id) REFERENCES {target_schema}.asientos_contables(id) ON DELETE SET NULL;
    """)

    # 2. Escudo Idempotente: Columnas de Candado Fiscal en Registro Tributario
    op.execute(f"""
        ALTER TABLE {target_schema}.registro_tributario
        ADD COLUMN IF NOT EXISTS exportado_ddjj BOOLEAN DEFAULT FALSE NOT NULL,
        ADD COLUMN IF NOT EXISTS fecha_exportacion TIMESTAMP WITH TIME ZONE;
    """)


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Rollback Seguro
    op.execute(f"""
        ALTER TABLE {target_schema}.registro_tributario DROP COLUMN IF EXISTS fecha_exportacion;
        ALTER TABLE {target_schema}.registro_tributario DROP COLUMN IF EXISTS exportado_ddjj;

        ALTER TABLE {target_schema}.asientos_contables DROP CONSTRAINT IF EXISTS fk_asientos_revertido;
        ALTER TABLE {target_schema}.asientos_contables DROP COLUMN IF EXISTS asiento_revertido_id;
        ALTER TABLE {target_schema}.asientos_contables DROP COLUMN IF EXISTS estado;
    """)