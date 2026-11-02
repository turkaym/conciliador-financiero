"""crear_secuencia_comprobantes_clearing

Revision ID: 7aa6de81a322
Revises: 55139b678211
Create Date: 2026-07-18 19:53:16.966998

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7aa6de81a322'
down_revision: Union[str, None] = '55139b678211'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🌟 DDL Defensivo: Creamos la secuencia nativa en el esquema del tenant
    op.execute(f"""
        CREATE SEQUENCE IF NOT EXISTS {target_schema}.clearing_cbte_seq START 1;
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🌟 Rollback Idempotente
    op.execute(f"""
        DROP SEQUENCE IF EXISTS {target_schema}.clearing_cbte_seq;
    """)