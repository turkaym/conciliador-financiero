"""staging_4_ojos_y_fix_lotes

Revision ID: e83c65ca9254
Revises: 011a7c9b9dfd
Create Date: 2026-06-26 13:35:55.233330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e83c65ca9254'
down_revision: Union[str, None] = '011a7c9b9dfd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # =========================================================
    # 1. SANEAMIENTO LEGACY: Formalizar el Big Bang de Lotes
    # (Para que los inquilinos nuevos nazcan con la estructura correcta)
    # =========================================================
    op.execute(f"""
        ALTER TABLE {target_schema}.lotes_pago
        ADD COLUMN IF NOT EXISTS cuenta_tesoreria_id INTEGER;

        ALTER TABLE {target_schema}.lotes_pago
        DROP COLUMN IF EXISTS cuenta_bancaria_id CASCADE;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_lotes_tesoreria' AND conrelid = '{target_schema}.lotes_pago'::regclass
            ) THEN
                ALTER TABLE {target_schema}.lotes_pago
                ADD CONSTRAINT fk_lotes_tesoreria
                FOREIGN KEY (cuenta_tesoreria_id) REFERENCES {target_schema}.cuentas_tesoreria(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)

    # =========================================================
    # 2. FASE 12.5: Tabla de Aislamiento para Flujo 4-Ojos
    # =========================================================
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {target_schema}.solicitudes_movimientos_tesoreria (
            id SERIAL PRIMARY KEY,
            cuenta_id INTEGER NOT NULL,
            tipo VARCHAR(20) NOT NULL,
            fecha DATE NOT NULL,
            monto NUMERIC(18, 2) NOT NULL,
            moneda VARCHAR(3) DEFAULT 'ARS' NOT NULL,
            concepto_crudo VARCHAR(255) NOT NULL,
            referencia_externa VARCHAR(100),
            hash_transaccional VARCHAR(64) NOT NULL,
            estado VARCHAR(30) DEFAULT 'PENDING_APPROVAL' NOT NULL,
            usuario_resolutor_id VARCHAR(50),
            motivo_rechazo TEXT,
            movimiento_definitivo_id INTEGER,

            -- Mixin de Auditoría
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

            CONSTRAINT fk_sol_mov_cuenta
                FOREIGN KEY (cuenta_id)
                REFERENCES {target_schema}.cuentas_tesoreria(id) ON DELETE CASCADE,

            CONSTRAINT fk_sol_mov_definitivo
                FOREIGN KEY (movimiento_definitivo_id)
                REFERENCES {target_schema}.movimientos_tesoreria(id) ON DELETE SET NULL
        );
    """)

    # Índices para la tabla de Staging
    op.execute(f"""
        CREATE INDEX IF NOT EXISTS ix_{target_schema}_sol_tesoreria_fecha ON {target_schema}.solicitudes_movimientos_tesoreria (fecha);
        CREATE INDEX IF NOT EXISTS ix_{target_schema}_sol_tesoreria_ref ON {target_schema}.solicitudes_movimientos_tesoreria (referencia_externa);
        CREATE INDEX IF NOT EXISTS ix_{target_schema}_sol_tesoreria_hash ON {target_schema}.solicitudes_movimientos_tesoreria (hash_transaccional);
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"DROP TABLE IF EXISTS {target_schema}.solicitudes_movimientos_tesoreria CASCADE;")