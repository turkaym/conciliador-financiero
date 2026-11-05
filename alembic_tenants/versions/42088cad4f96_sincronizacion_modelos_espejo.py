"""sincronizacion_modelos_espejo

Revision ID: 42088cad4f96
Revises: 9842ad2e86c2
Create Date: 2026-07-01 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '42088cad4f96'
down_revision: Union[str, None] = '9842ad2e86c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 1. Materialización de tablas huérfanas (Módulo de Conciliación)
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {target_schema}.match_detalles_movimientos (
            id SERIAL PRIMARY KEY,
            match_id INTEGER NOT NULL REFERENCES {target_schema}.conciliacion_matches(id) ON DELETE CASCADE,
            movimiento_id INTEGER NOT NULL,
            monto_aplicado NUMERIC(15, 2) NOT NULL
        );
    """)
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {target_schema}.match_detalles_comprobantes (
            id SERIAL PRIMARY KEY,
            match_id INTEGER NOT NULL REFERENCES {target_schema}.conciliacion_matches(id) ON DELETE CASCADE,
            comprobante_id INTEGER NOT NULL,
            monto_aplicado NUMERIC(15, 2) NOT NULL
        );
    """)

    # 2. Materialización de columnas faltantes (Módulo Bancario)
    op.execute(f"""
        ALTER TABLE {target_schema}.movimientos_bancarios
        ADD COLUMN IF NOT EXISTS usuario_resolutor_id VARCHAR(50),
        ADD COLUMN IF NOT EXISTS motivo_rechazo TEXT;
    """)

    # 3. Alineación de Precisión Matemática (De 15,2 a 18,2 según el modelo Python)
    op.execute(f"ALTER TABLE {target_schema}.comprobantes ALTER COLUMN importe_exento TYPE NUMERIC(18, 2);")
    op.execute(f"ALTER TABLE {target_schema}.cuentas_bancarias ALTER COLUMN saldo_actual TYPE NUMERIC(18, 2);")
    op.execute(f"ALTER TABLE {target_schema}.movimientos_bancarios ALTER COLUMN monto TYPE NUMERIC(18, 2);")
    op.execute(f"ALTER TABLE {target_schema}.movimientos_bancarios ALTER COLUMN saldo_pendiente TYPE NUMERIC(18, 2);")
    op.execute(f"ALTER TABLE {target_schema}.movimientos_bancarios ALTER COLUMN saldo_resultante TYPE NUMERIC(18, 2);")

    # 4. Alineación de restricciones de unicidad (API Keys)
    op.execute(f"ALTER TABLE {target_schema}.api_keys DROP CONSTRAINT IF EXISTS uix_api_key_prefix;")
    op.execute(f"ALTER TABLE {target_schema}.api_keys ADD CONSTRAINT uix_api_key_prefix UNIQUE (prefix);")


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"ALTER TABLE {target_schema}.movimientos_bancarios DROP COLUMN IF EXISTS usuario_resolutor_id;")
    op.execute(f"ALTER TABLE {target_schema}.movimientos_bancarios DROP COLUMN IF EXISTS motivo_rechazo;")
    op.execute(f"DROP TABLE IF EXISTS {target_schema}.match_detalles_comprobantes CASCADE;")
    op.execute(f"DROP TABLE IF EXISTS {target_schema}.match_detalles_movimientos CASCADE;")