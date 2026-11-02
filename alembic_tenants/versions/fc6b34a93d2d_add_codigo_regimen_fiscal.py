"""add_codigo_regimen_fiscal

Revision ID: fc6b34a93d2d
Revises: 42088cad4f96
Create Date: 2026-07-02 11:58:31.143665

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc6b34a93d2d'
down_revision: Union[str, None] = '42088cad4f96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Inyección idempotente del código de régimen AFIP para el Sifón Fiscal
    op.execute(f"""
        ALTER TABLE {target_schema}.reglas_impuestos
        ADD COLUMN IF NOT EXISTS codigo_regimen_afip INTEGER DEFAULT 217 NOT NULL;
    """)


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Reversión segura
    op.execute(f"""
        ALTER TABLE {target_schema}.reglas_impuestos
        DROP COLUMN IF EXISTS codigo_regimen_afip;
    """)