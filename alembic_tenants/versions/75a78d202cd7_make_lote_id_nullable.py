"""make_lote_id_nullable

Revision ID: 75a78d202cd7
Revises: 3cdc359084bd
Create Date: 2026-07-13 19:09:21.707021

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75a78d202cd7'
down_revision: Union[str, None] = '3cdc359084bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # DDL Defensivo: Relajar la cardinalidad permitiendo que lote_id sea nulo.
    # PostgreSQL ignora el comando si la columna ya es nullable, haciéndolo seguro e idempotente.
    op.execute(f"""
        ALTER TABLE {target_schema}.lote_pago_detalles
        ALTER COLUMN lote_id DROP NOT NULL;
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Rollback: Restablecer la restricción (solo funcionará si no hay nulos en la tabla en ese momento)
    op.execute(f"""
        ALTER TABLE {target_schema}.lote_pago_detalles
        ALTER COLUMN lote_id SET NOT NULL;
    """)