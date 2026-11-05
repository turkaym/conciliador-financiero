"""refactor_ledger_tesoreria_y_matching

Revision ID: 830c1bbd17ec
Revises: e83c65ca9254
Create Date: 2026-06-28 21:34:15.370527

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '830c1bbd17ec'
down_revision: Union[str, None] = 'e83c65ca9254'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    if not target_schema:
        return

    # ==========================================
    # 1. EXTENSIÓN DEL LEDGER DE TESORERÍA
    # ==========================================
    op.execute(f"""
        ALTER TABLE {target_schema}.movimientos_tesoreria
        ADD COLUMN IF NOT EXISTS saldo_pendiente NUMERIC(18, 2);
    """)

    # Inicializamos el saldo pendiente con el monto original de forma retroactiva (si había datos previos)
    op.execute(f"""
        UPDATE {target_schema}.movimientos_tesoreria
        SET saldo_pendiente = ABS(monto)
        WHERE saldo_pendiente IS NULL;
    """)

    # Aplicamos la restricción de No Nulo de forma segura
    op.execute(f"""
        ALTER TABLE {target_schema}.movimientos_tesoreria
        ALTER COLUMN saldo_pendiente SET NOT NULL;
    """)

    # Índice para alta performance en búsquedas del Motor Automático
    op.execute(f"""
        CREATE INDEX IF NOT EXISTS ix_{target_schema}_mov_tesoreria_saldo_pend
        ON {target_schema}.movimientos_tesoreria (saldo_pendiente);
    """)

    # ==========================================
    # 2. MIGRACIÓN DEL PEGAMENTO DE CONCILIACIÓN
    # ==========================================
    op.execute(f"""
        ALTER TABLE {target_schema}.match_detalle_movimientos
        ADD COLUMN IF NOT EXISTS movimiento_tesoreria_id INTEGER;
    """)

    # Borrado quirúrgico de la vieja clave foránea (Idempotente)
    op.execute(f"""
        DO $$
        DECLARE
            fk_name text;
        BEGIN
            SELECT constraint_name INTO fk_name
            FROM information_schema.key_column_usage
            WHERE table_schema = '{target_schema}'
              AND table_name = 'match_detalle_movimientos'
              AND column_name = 'movimiento_id';

            IF fk_name IS NOT NULL THEN
                EXECUTE 'ALTER TABLE {target_schema}.match_detalle_movimientos DROP CONSTRAINT IF EXISTS ' || fk_name;
            END IF;
        END $$;
    """)

    op.execute(f"""
        ALTER TABLE {target_schema}.match_detalle_movimientos
        DROP COLUMN IF EXISTS movimiento_id CASCADE;
    """)

    # Creación de la nueva relación hacia Tesorería (Idempotente)
    op.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_match_detalle_mov_tes_id'
                AND connamespace = '{target_schema}'::regnamespace
            ) THEN
                ALTER TABLE {target_schema}.match_detalle_movimientos
                ADD CONSTRAINT fk_match_detalle_mov_tes_id
                FOREIGN KEY (movimiento_tesoreria_id) REFERENCES {target_schema}.movimientos_tesoreria(id) ON DELETE CASCADE;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    if not target_schema:
        return

    # ==========================================
    # 1. ROLLBACK DEL PEGAMENTO DE CONCILIACIÓN
    # ==========================================
    op.execute(f"""
        ALTER TABLE {target_schema}.match_detalle_movimientos
        ADD COLUMN IF NOT EXISTS movimiento_id INTEGER;
    """)

    op.execute(f"""
        ALTER TABLE {target_schema}.match_detalle_movimientos
        DROP CONSTRAINT IF EXISTS fk_match_detalle_mov_tes_id;
    """)

    op.execute(f"""
        ALTER TABLE {target_schema}.match_detalle_movimientos
        DROP COLUMN IF EXISTS movimiento_tesoreria_id CASCADE;
    """)

    # ==========================================
    # 2. ROLLBACK DEL LEDGER DE TESORERÍA
    # ==========================================
    op.execute(f"""
        DROP INDEX IF EXISTS {target_schema}.ix_{target_schema}_mov_tesoreria_saldo_pend;
    """)

    op.execute(f"""
        ALTER TABLE {target_schema}.movimientos_tesoreria
        DROP COLUMN IF EXISTS saldo_pendiente CASCADE;
    """)