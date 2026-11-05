"""crear_tabla_reglas_impuesto

Revision ID: 2b27979a6f0d
Revises: fc6b34a93d2d
Create Date: 2026-07-04 22:56:40.898834

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b27979a6f0d'
down_revision: Union[str, None] = 'fc6b34a93d2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🌟 DDL Defensivo: Inyección de columnas faltantes en la tabla existente (Plural)
    op.execute(f"""
        ALTER TABLE {target_schema}.reglas_impuestos
        ADD COLUMN IF NOT EXISTS codigo_regimen_afip INTEGER DEFAULT 217 NOT NULL,
        ADD COLUMN IF NOT EXISTS monto_minimo_sujeto NUMERIC(15, 2) DEFAULT 0.0 NOT NULL,
        ADD COLUMN IF NOT EXISTS aplica_padron BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS cuenta_contable_id INTEGER;
    """)

    # Inyección de FK Segura e Idempotente usando bloque DO
    op.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_reglas_impuestos_cuenta'
                AND connamespace = '{target_schema}'::regnamespace
            ) THEN
                ALTER TABLE {target_schema}.reglas_impuestos
                ADD CONSTRAINT fk_reglas_impuestos_cuenta FOREIGN KEY (cuenta_contable_id)
                REFERENCES {target_schema}.plan_cuentas(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🌟 Downgrade Defensivo: DROP IF EXISTS de las columnas agregadas
    op.execute(f"""
        ALTER TABLE {target_schema}.reglas_impuestos
        DROP COLUMN IF EXISTS codigo_regimen_afip,
        DROP COLUMN IF EXISTS monto_minimo_sujeto,
        DROP COLUMN IF EXISTS aplica_padron,
        DROP COLUMN IF EXISTS cuenta_contable_id CASCADE;
    """)