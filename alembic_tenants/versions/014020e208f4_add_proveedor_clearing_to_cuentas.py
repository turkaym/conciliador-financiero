"""add_proveedor_clearing_to_cuentas

Revision ID: 014020e208f4
Revises: 09e89e721f64
Create Date: 2026-07-18 02:41:38.273953

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '014020e208f4'
down_revision: Union[str, None] = '09e89e721f64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # DDL Defensivo: Agregamos la columna a Cuentas de Tesorería
    op.execute(f"""
        ALTER TABLE {target_schema}.cuentas_tesoreria
        ADD COLUMN IF NOT EXISTS proveedor_clearing_id INTEGER REFERENCES {target_schema}.contactos_comerciales(id) ON DELETE SET NULL;
    """)

    # DDL Defensivo: Agregamos la columna a Cuentas Bancarias
    op.execute(f"""
        ALTER TABLE {target_schema}.cuentas_bancarias
        ADD COLUMN IF NOT EXISTS proveedor_clearing_id INTEGER REFERENCES {target_schema}.contactos_comerciales(id) ON DELETE SET NULL;
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Rollback Defensivo
    op.execute(f"""
        ALTER TABLE {target_schema}.cuentas_tesoreria
        DROP COLUMN IF EXISTS proveedor_clearing_id;
    """)

    op.execute(f"""
        ALTER TABLE {target_schema}.cuentas_bancarias
        DROP COLUMN IF EXISTS proveedor_clearing_id;
    """)