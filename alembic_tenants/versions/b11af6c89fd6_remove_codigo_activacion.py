"""remove_codigo_activacion

Revision ID: b11af6c89fd6
Revises: 0bff03d1f28e
Create Date: 2026-05-22 16:42:50.502131

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b11af6c89fd6'
down_revision: Union[str, None] = '0bff03d1f28e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🛡️ Escudo de Idempotencia: Destrucción de tabla obsoleta usando SQL nativo
    op.execute(f"""
        DROP TABLE IF EXISTS {target_schema}.codigos_activacion CASCADE;
    """)


def downgrade() -> None:
    # Eliminación arquitectónica. No se requiere rollback.
    pass