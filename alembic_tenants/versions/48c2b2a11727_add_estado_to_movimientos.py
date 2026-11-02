"""add_estado_to_movimientos

Revision ID: 48c2b2a11727
Revises: aa7b7171d451
Create Date: 2026-05-08 10:55:55.558123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48c2b2a11727'
down_revision = '9621188d2e5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Inyección Idempotente SQL (Política v4.0)
    op.execute(f"""
        ALTER TABLE {target_schema}.movimientos_bancarios
        ADD COLUMN IF NOT EXISTS estado VARCHAR(50) DEFAULT 'APROBADO';
    """)

    op.execute(f"""
        CREATE INDEX IF NOT EXISTS ix_{target_schema}_mov_bancarios_estado
        ON {target_schema}.movimientos_bancarios (estado);
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"DROP INDEX IF EXISTS {target_schema}.ix_{target_schema}_mov_bancarios_estado;")
    op.execute(f"ALTER TABLE {target_schema}.movimientos_bancarios DROP COLUMN IF EXISTS estado;")