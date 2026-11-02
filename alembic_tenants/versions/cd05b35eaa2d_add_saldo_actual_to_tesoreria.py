"""add_saldo_actual_to_tesoreria

Revision ID: cd05b35eaa2d
Revises: 13fcad8994de
Create Date: 2026-06-10 18:12:16.562740

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd05b35eaa2d'
down_revision: Union[str, None] = '13fcad8994de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Escudo de Idempotencia (SQL Crudo) para alterar la tabla existente de forma segura
    op.execute(f"""
        ALTER TABLE {target_schema}.cuentas_tesoreria
        ADD COLUMN IF NOT EXISTS saldo_actual NUMERIC(15,2) DEFAULT 0.00 NOT NULL;
    """)


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Downgrade Defensivo (SQL Crudo)
    op.execute(f"""
        ALTER TABLE {target_schema}.cuentas_tesoreria
        DROP COLUMN IF EXISTS saldo_actual;
    """)