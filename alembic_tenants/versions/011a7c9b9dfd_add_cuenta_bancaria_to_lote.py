"""add_cuenta_bancaria_to_lote

Revision ID: 011a7c9b9dfd
Revises: b3da9b179694
Create Date: 2026-06-23 13:15:00.490925

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011a7c9b9dfd'
down_revision: Union[str, None] = 'b3da9b179694'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 1. Agregamos la nueva columna hacia Tesorería
    op.execute(f"""
        ALTER TABLE {target_schema}.lotes_pago
        ADD COLUMN IF NOT EXISTS cuenta_tesoreria_id INTEGER;
    """)

    # 2. Inyectamos la Llave Foránea mediante un bloque DO para garantizar idempotencia en PostgreSQL
    op.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_lotes_pago_tesoreria' AND conrelid = '{target_schema}.lotes_pago'::regclass
            ) THEN
                ALTER TABLE {target_schema}.lotes_pago
                ADD CONSTRAINT fk_lotes_pago_tesoreria
                FOREIGN KEY (cuenta_tesoreria_id) REFERENCES {target_schema}.cuentas_tesoreria(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)

    # 3. BIG BANG: Extirpamos la columna Legacy en cascada para destruir sus llaves foráneas antiguas
    op.execute(f"""
        ALTER TABLE {target_schema}.lotes_pago
        DROP COLUMN IF EXISTS cuenta_bancaria_id CASCADE;
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Restauración Defensiva
    op.execute(f"""
        ALTER TABLE {target_schema}.lotes_pago
        ADD COLUMN IF NOT EXISTS cuenta_bancaria_id INTEGER;
    """)

    op.execute(f"""
        ALTER TABLE {target_schema}.lotes_pago
        DROP COLUMN IF EXISTS cuenta_tesoreria_id CASCADE;
    """)