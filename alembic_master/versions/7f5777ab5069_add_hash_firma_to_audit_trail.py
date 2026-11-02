"""add_hash_firma_to_audit_trail

Revision ID: 7f5777ab5069
Revises: f77f7640036a
Create Date: 2026-05-06 16:57:00.951980

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f5777ab5069'
down_revision: Union[str, None] = 'f77f7640036a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregamos la columna con un valor por defecto para no romper registros existentes
    op.add_column('audit_trail', sa.Column('hash_firma', sa.String(length=64), server_default='LEGACY_MIGRATION', nullable=False))
    op.create_index(op.f('ix_public_audit_trail_hash_firma'), 'audit_trail', ['hash_firma'], unique=False, schema='public')


def downgrade() -> None:
    op.drop_index(op.f('ix_public_audit_trail_hash_firma'), table_name='audit_trail', schema='public')
    op.drop_column('audit_trail', 'hash_firma')