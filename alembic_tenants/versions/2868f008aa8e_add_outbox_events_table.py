"""add_outbox_events_table

Revision ID: 2868f008aa8e
Revises: c0dc4d038402
Create Date: 2026-05-10 21:30:21.772636

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2868f008aa8e'
down_revision: Union[str, None] = 'c0dc4d038402'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {target_schema}.outbox_events (
            id SERIAL PRIMARY KEY,
            aggregate_type VARCHAR(50) NOT NULL,
            payload JSONB NOT NULL,
            status VARCHAR(20) DEFAULT 'PENDING' NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_{target_schema}_outbox_status ON {target_schema}.outbox_events (status);
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"DROP TABLE IF EXISTS {target_schema}.outbox_events;")