"""despliegue_motor_fiscal

Revision ID: 9842ad2e86c2
Revises: 830c1bbd17ec
Create Date: 2026-07-01 17:51:02.979927

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9842ad2e86c2'
down_revision: Union[str, None] = '830c1bbd17ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 1. Corrección Arquitectónica: Inyección defensiva de columna en tabla existente
    op.execute(f"""
        ALTER TABLE {target_schema}.secuencias_fiscales
        ADD COLUMN IF NOT EXISTS entidad_id INTEGER REFERENCES {target_schema}.razones_sociales_propias(id) ON DELETE CASCADE;
    """)

    # Seteamos un valor por defecto seguro (1) para los registros que ya existan antes de aplicar el NOT NULL
    op.execute(f"""
        UPDATE {target_schema}.secuencias_fiscales
        SET entidad_id = 1
        WHERE entidad_id IS NULL;
    """)

    op.execute(f"""
        ALTER TABLE {target_schema}.secuencias_fiscales
        ALTER COLUMN entidad_id SET NOT NULL;
    """)

    # Reestructuración del constraint único para incluir el aislamiento por entidad
    op.execute(f"""
        ALTER TABLE {target_schema}.secuencias_fiscales
        DROP CONSTRAINT IF EXISTS uix_ptovta_tipocbte;
    """)
    op.execute(f"""
        ALTER TABLE {target_schema}.secuencias_fiscales
        ADD CONSTRAINT uix_ptovta_tipocbte UNIQUE (entidad_id, punto_venta, tipo_cbte);
    """)

    # 2. Creación Idempotente: padrones_fiscales
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {target_schema}.padrones_fiscales (
            cuit VARCHAR(11) NOT NULL,
            jurisdiccion VARCHAR(50) NOT NULL,
            periodo VARCHAR(6) NOT NULL,
            alicuota_retencion NUMERIC(7,4) DEFAULT 0.0 NOT NULL,
            alicuota_percepcion NUMERIC(7,4) DEFAULT 0.0 NOT NULL,
            coeficiente_riesgo NUMERIC(5,2),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            created_by_id VARCHAR(255),
            updated_by_id VARCHAR(255),
            PRIMARY KEY (cuit, jurisdiccion, periodo)
        );
    """)

    # 3. Creación Idempotente: reglas_impuestos
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {target_schema}.reglas_impuestos (
            id SERIAL PRIMARY KEY,
            entidad_id INTEGER NOT NULL REFERENCES {target_schema}.razones_sociales_propias(id) ON DELETE CASCADE,
            tipo_impuesto VARCHAR(50) NOT NULL,
            jurisdiccion VARCHAR(50) NOT NULL,
            alicuota_defecto NUMERIC(7,4) DEFAULT 0.0 NOT NULL,
            monto_minimo_sujeto NUMERIC(15,2) DEFAULT 0.0 NOT NULL,
            aplica_padron BOOLEAN DEFAULT FALSE NOT NULL,
            cuenta_contable_id INTEGER REFERENCES {target_schema}.plan_cuentas(id) ON DELETE SET NULL,
            is_active BOOLEAN DEFAULT TRUE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            created_by_id VARCHAR(255),
            updated_by_id VARCHAR(255),
            CONSTRAINT uix_regla_impuesto_entidad UNIQUE (entidad_id, tipo_impuesto, jurisdiccion)
        );
    """)
    op.execute(f"""
        CREATE INDEX IF NOT EXISTS ix_reglas_impuestos_id
        ON {target_schema}.reglas_impuestos (id);
    """)


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Eliminación Defensiva (Cascada para evitar bloqueos por dependencias)
    op.execute(f"DROP TABLE IF EXISTS {target_schema}.reglas_impuestos CASCADE;")
    op.execute(f"DROP TABLE IF EXISTS {target_schema}.padrones_fiscales CASCADE;")
    op.execute(f"DROP TABLE IF EXISTS {target_schema}.secuencias_fiscales CASCADE;")