"""add_usuario_creador_id_to_movimientos

Revision ID: 656e6300ca20
Revises: 2868f008aa8e
Create Date: 2026-05-10 21:53:24.554269

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '656e6300ca20'
down_revision: Union[str, None] = '2868f008aa8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"""
        ALTER TABLE {target_schema}.movimientos_bancarios
        ADD COLUMN IF NOT EXISTS usuario_creador_id VARCHAR(50) DEFAULT 'SYSTEM' NOT NULL;
    """)
    op.execute(f"""
        CREATE INDEX IF NOT EXISTS ix_{target_schema}_mov_usuario_creador
        ON {target_schema}.movimientos_bancarios (usuario_creador_id);
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"DROP INDEX IF EXISTS {target_schema}.ix_{target_schema}_mov_usuario_creador;")
    op.execute(f"ALTER TABLE {target_schema}.movimientos_bancarios DROP COLUMN IF EXISTS usuario_creador_id;")