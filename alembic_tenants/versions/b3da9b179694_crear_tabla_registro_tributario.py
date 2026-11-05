"""crear_tabla_registro_tributario

Revision ID: b3da9b179694
Revises: e248eabed866
Create Date: 2026-06-16 21:26:37.005260

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3da9b179694'
down_revision: Union[str, None] = 'e248eabed866'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Escudo de Idempotencia (SQL Crudo) para creación de tabla y sus índices
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS "{target_schema}".registro_tributario (
            id SERIAL PRIMARY KEY,
            entidad_id INTEGER NOT NULL REFERENCES "{target_schema}".razones_sociales_propias(id),
            clase_tributo VARCHAR(20) NOT NULL,
            tipo_impuesto VARCHAR(50) NOT NULL,
            jurisdiccion VARCHAR(50) DEFAULT 'AFIP' NOT NULL,
            cuit_sujeto VARCHAR(11) NOT NULL,
            razon_social_sujeto VARCHAR(255) NOT NULL,
            fecha_registro DATE NOT NULL,
            comprobante_id INTEGER,
            asiento_id INTEGER REFERENCES "{target_schema}".asientos_contables(id),
            numero_comprobante_origen VARCHAR(50),
            numero_certificado VARCHAR(50),
            base_imponible NUMERIC(15, 2) NOT NULL,
            alicuota_aplicada NUMERIC(5, 2) NOT NULL,
            monto_impuesto NUMERIC(15, 2) NOT NULL,
            periodo_fiscal VARCHAR(6) NOT NULL,
            origen_alicuota VARCHAR(50) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_reg_trib_clase_{target_schema} ON "{target_schema}".registro_tributario (clase_tributo);
        CREATE INDEX IF NOT EXISTS ix_reg_trib_tipo_{target_schema} ON "{target_schema}".registro_tributario (tipo_impuesto);
        CREATE INDEX IF NOT EXISTS ix_reg_trib_cuit_{target_schema} ON "{target_schema}".registro_tributario (cuit_sujeto);
        CREATE INDEX IF NOT EXISTS ix_reg_trib_periodo_{target_schema} ON "{target_schema}".registro_tributario (periodo_fiscal);
        CREATE UNIQUE INDEX IF NOT EXISTS uix_reg_trib_cert_{target_schema} ON "{target_schema}".registro_tributario (numero_certificado);
    """)


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Rollback Idempotente
    op.execute(f"""
        DROP TABLE IF EXISTS "{target_schema}".registro_tributario CASCADE;
    """)