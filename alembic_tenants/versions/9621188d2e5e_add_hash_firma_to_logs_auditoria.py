"""add_hash_firma_to_logs_auditoria

Revision ID: 9621188d2e5e
Revises: # (asegurate de dejar el down_revision que tenías autogenerado)
Create Date: 2026-05-06 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9621188d2e5e'
# 👇 REEMPLAZÁ ESTO POR EL HASH DE TU DOWN_REVISION ORIGINAL SI LO TENÉS, SINO DEJALO EN NONE
down_revision = '1918f9f404b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🌟 ESCUDO DE IDEMPOTENCIA (SQL Crudo Nativo PostgreSQL)
    # Ignora silenciosamente si la columna o el índice ya existen por inconsistencias previas
    op.execute(f"""
        ALTER TABLE {target_schema}.logs_auditoria
        ADD COLUMN IF NOT EXISTS hash_firma VARCHAR(64) DEFAULT 'LEGACY_MIGRATION' NOT NULL;
    """)

    op.execute(f"""
        CREATE INDEX IF NOT EXISTS ix_{target_schema}_logs_auditoria_hash_firma
        ON {target_schema}.logs_auditoria (hash_firma);
    """)


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Reversión segura
    op.execute(f"DROP INDEX IF EXISTS {target_schema}.ix_{target_schema}_logs_auditoria_hash_firma;")
    op.execute(f"ALTER TABLE {target_schema}.logs_auditoria DROP COLUMN IF EXISTS hash_firma;")