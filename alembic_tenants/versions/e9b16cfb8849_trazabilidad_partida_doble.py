"""trazabilidad_partida_doble

Revision ID: e9b16cfb8849
Revises: 015512d422ae
Create Date: 2026-07-19 05:37:33.608013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9b16cfb8849'
down_revision: Union[str, None] = '015512d422ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Escudo Idempotente: Agregar cuenta_contable_id a cajas de tesorería
    op.execute(f"""
        ALTER TABLE {target_schema}.cuentas_tesoreria
        ADD COLUMN IF NOT EXISTS cuenta_contable_id INTEGER,
        ADD CONSTRAINT fk_cuentas_tesoreria_cuenta_contable
        FOREIGN KEY (cuenta_contable_id) REFERENCES {target_schema}.plan_cuentas(id) ON DELETE SET NULL;
    """)

    # Escudo Idempotente: Agregar asiento_id a movimientos
    op.execute(f"""
        ALTER TABLE {target_schema}.movimientos_tesoreria
        ADD COLUMN IF NOT EXISTS asiento_id INTEGER,
        ADD CONSTRAINT fk_mov_tesoreria_asiento
        FOREIGN KEY (asiento_id) REFERENCES {target_schema}.asientos_contables(id) ON DELETE SET NULL;
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Rollback Seguro
    op.execute(f"""
        ALTER TABLE {target_schema}.movimientos_tesoreria DROP CONSTRAINT IF EXISTS fk_mov_tesoreria_asiento;
        ALTER TABLE {target_schema}.movimientos_tesoreria DROP COLUMN IF EXISTS asiento_id;

        ALTER TABLE {target_schema}.cuentas_tesoreria DROP CONSTRAINT IF EXISTS fk_cuentas_tesoreria_cuenta_contable;
        ALTER TABLE {target_schema}.cuentas_tesoreria DROP COLUMN IF EXISTS cuenta_contable_id;
    """)