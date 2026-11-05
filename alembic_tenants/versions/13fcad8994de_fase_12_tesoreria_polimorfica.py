"""fase_12_tesoreria_polimorfica

Revision ID: 13fcad8994de
Revises: 195729d72bfa
Create Date: 2026-06-08 01:56:08.995657

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '13fcad8994de'
down_revision: Union[str, None] = '195729d72bfa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Escudo de Idempotencia: DDL Defensivo para Ecosistema Polimórfico
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS "{target_schema}".cuentas_tesoreria (
            id SERIAL PRIMARY KEY,
            entidad_id INTEGER NOT NULL CONSTRAINT fk_cta_tesoreria_entidad REFERENCES "{target_schema}".razones_sociales_propias (id) ON DELETE CASCADE,
            nombre VARCHAR(100) NOT NULL,
            tipo_cuenta VARCHAR(30) NOT NULL,
            moneda VARCHAR(3) DEFAULT 'ARS' NOT NULL,
            cbu_cvu VARCHAR(22),
            alias VARCHAR(50),
            numero_cuenta VARCHAR(50),
            is_active BOOLEAN DEFAULT TRUE NOT NULL,
            is_virtual_clearing BOOLEAN DEFAULT FALSE NOT NULL,
            is_default_cash BOOLEAN DEFAULT FALSE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
    """)

    op.execute(f"""
        CREATE TABLE IF NOT EXISTS "{target_schema}".movimientos_tesoreria (
            id SERIAL PRIMARY KEY,
            cuenta_id INTEGER NOT NULL CONSTRAINT fk_mov_tesoreria_cuenta REFERENCES "{target_schema}".cuentas_tesoreria (id) ON DELETE CASCADE,
            tipo VARCHAR(20) NOT NULL,
            fecha DATE NOT NULL,
            monto NUMERIC(18, 2) NOT NULL,
            moneda VARCHAR(3) DEFAULT 'ARS' NOT NULL,
            concepto_crudo VARCHAR(255) NOT NULL,
            referencia_externa VARCHAR(100),
            hash_transaccional VARCHAR(64) NOT NULL,
            comprobante_id INTEGER CONSTRAINT fk_mov_tes_comprobante REFERENCES "{target_schema}".comprobantes (id) ON DELETE SET NULL,
            anulado BOOLEAN DEFAULT FALSE NOT NULL,
            motivo_anulacion TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT uix_mov_tesoreria_unico_hash UNIQUE (cuenta_id, hash_transaccional)
        );
    """)

    # Índices Estratégicos y de Búsqueda Trigram
    op.execute(f"""
        CREATE INDEX IF NOT EXISTS ix_mov_tes_fecha ON "{target_schema}".movimientos_tesoreria (fecha);
        CREATE INDEX IF NOT EXISTS ix_mov_tes_hash ON "{target_schema}".movimientos_tesoreria (hash_transaccional);
        CREATE INDEX IF NOT EXISTS ix_mov_tes_ref ON "{target_schema}".movimientos_tesoreria (referencia_externa);
        CREATE INDEX IF NOT EXISTS ix_mov_tes_busqueda ON "{target_schema}".movimientos_tesoreria USING gin (concepto_crudo gin_trgm_ops);
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Rollback Defensivo con CASCADE para demoler dependencias sin trabar el multiplexor
    op.execute(f'DROP TABLE IF EXISTS "{target_schema}".movimientos_tesoreria CASCADE;')
    op.execute(f'DROP TABLE IF EXISTS "{target_schema}".cuentas_tesoreria CASCADE;')