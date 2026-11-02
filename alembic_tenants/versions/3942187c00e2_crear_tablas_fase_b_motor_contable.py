"""crear_tablas_fase_b_motor_contable

Revision ID: 3942187c00e2
Revises: d16e3fd88484
Create Date: 2026-06-16 12:47:08.230553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3942187c00e2'
down_revision: Union[str, None] = 'd16e3fd88484'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    if not target_schema:
        raise ValueError("No se pudo determinar el schema objetivo para la migración.")

    # 1. Tabla: conciliacion_matches
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {target_schema}.conciliacion_matches (
            id SERIAL PRIMARY KEY,
            score NUMERIC(3, 2) NOT NULL,
            metodo VARCHAR(50) NOT NULL,
            fecha_match TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        );
    """)

    # 2. Tabla: asientos_contables
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {target_schema}.asientos_contables (
            id SERIAL PRIMARY KEY,
            fecha DATE NOT NULL,
            concepto VARCHAR(255) NOT NULL,
            match_id INTEGER REFERENCES {target_schema}.conciliacion_matches(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

    # 3. Tabla: lineas_asientos
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {target_schema}.lineas_asientos (
            id SERIAL PRIMARY KEY,
            asiento_id INTEGER NOT NULL REFERENCES {target_schema}.asientos_contables(id) ON DELETE CASCADE,
            cuenta_id INTEGER NOT NULL,
            debe NUMERIC(15, 2) DEFAULT 0.00 NOT NULL,
            haber NUMERIC(15, 2) DEFAULT 0.00 NOT NULL
        );
    """)

    # 4. Tabla intermedia: match_detalles_comprobantes
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {target_schema}.match_detalles_comprobantes (
            id SERIAL PRIMARY KEY,
            match_id INTEGER NOT NULL REFERENCES {target_schema}.conciliacion_matches(id) ON DELETE CASCADE,
            comprobante_id INTEGER NOT NULL,
            monto_aplicado NUMERIC(15, 2) NOT NULL
        );
    """)

    # 5. Tabla intermedia: match_detalles_movimientos
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {target_schema}.match_detalles_movimientos (
            id SERIAL PRIMARY KEY,
            match_id INTEGER NOT NULL REFERENCES {target_schema}.conciliacion_matches(id) ON DELETE CASCADE,
            movimiento_id INTEGER NOT NULL,
            monto_aplicado NUMERIC(15, 2) NOT NULL
        );
    """)


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    if not target_schema:
        raise ValueError("No se pudo determinar el schema objetivo para la reversión.")

    # Eliminación en orden inverso respetando las restricciones de clave foránea
    op.execute(f"DROP TABLE IF EXISTS {target_schema}.match_detalles_movimientos CASCADE;")
    op.execute(f"DROP TABLE IF EXISTS {target_schema}.match_detalles_comprobantes CASCADE;")
    op.execute(f"DROP TABLE IF EXISTS {target_schema}.lineas_asientos CASCADE;")
    op.execute(f"DROP TABLE IF EXISTS {target_schema}.asientos_contables CASCADE;")
    op.execute(f"DROP TABLE IF EXISTS {target_schema}.conciliacion_matches CASCADE;")