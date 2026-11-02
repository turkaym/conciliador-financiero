"""precision_fiscal_y_auditoria_estricta

Revision ID: 8163dcf8c740
Revises: fef62fbaaf45
Create Date: 2026-04-23 16:56:03.129609

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8163dcf8c740'
down_revision: Union[str, None] = 'fef62fbaaf45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # ---------------------------------------------------------
    # 1. ESCALADO FISCAL (AFIP) - Modificación declarativa pura
    # ---------------------------------------------------------
    op.alter_column('comprobantes_tributos', 'alicuota',
                    type_=sa.Numeric(7, 4),
                    existing_type=sa.Numeric(5, 2),
                    schema=target_schema)

    op.alter_column('reglas_impuestos', 'alicuota_defecto',
                    type_=sa.Numeric(7, 4),
                    existing_type=sa.Numeric(5, 2),
                    schema=target_schema)

    op.alter_column('padrones_fiscales', 'alicuota_retencion',
                    type_=sa.Numeric(7, 4),
                    existing_type=sa.Numeric(5, 2),
                    schema=target_schema)

    op.alter_column('padrones_fiscales', 'alicuota_percepcion',
                    type_=sa.Numeric(7, 4),
                    existing_type=sa.Numeric(5, 2),
                    schema=target_schema)

    # ---------------------------------------------------------
    # 2. SANITIZACIÓN DE IDENTIDADES - Casteo explícito PG
    # ---------------------------------------------------------
    # Cambiar de Integer a Varchar requiere instrucción USING nativa
    op.alter_column('periodos_contables', 'cerrado_por_id',
                    type_=sa.String(255),
                    existing_type=sa.Integer(),
                    schema=target_schema,
                    postgresql_using="cerrado_por_id::varchar(255)")

    # ---------------------------------------------------------
    # 3. ESCUDO MATEMÁTICO B2B - Idempotencia SQL Nativa
    # ---------------------------------------------------------
    op.execute(f"""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'chk_importe_total_positivo'
            AND conrelid = '{target_schema}.comprobantes'::regclass
        ) THEN
            ALTER TABLE {target_schema}.comprobantes ADD CONSTRAINT chk_importe_total_positivo CHECK (importe_total >= 0);
        END IF;
    END
    $$;
    """)

    # ---------------------------------------------------------
    # 4. INYECCIÓN DEL MIXIN (Audit Trail) - Idempotencia SQL Nativa
    # ---------------------------------------------------------
    tablas_auditables = [
        'razones_sociales_propias', 'codigos_activacion', 'usuario_entidad_roles',
        'comprobantes', 'cuentas_bancarias', 'movimientos_bancarios',
        'logs_auditoria', 'reglas_aprendizaje', 'plan_cuentas',
        'asientos_contables', 'cola_mensajes_muertos', 'reglas_impuestos',
        'padrones_fiscales', 'historial_cotizaciones', 'webhook_subscriptions',
        'webhook_delivery_logs'
    ]

    for tabla in tablas_auditables:
        # Agrega la columna updated_at si no existe, garantizando que el Mixin no rompa en tablas viejas
        op.execute(f"ALTER TABLE {target_schema}.{tabla} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE")


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # Reversión de los campos numéricos
    op.alter_column('padrones_fiscales', 'alicuota_percepcion', type_=sa.Numeric(5, 2), existing_type=sa.Numeric(7, 4), schema=target_schema)
    op.alter_column('padrones_fiscales', 'alicuota_retencion', type_=sa.Numeric(5, 2), existing_type=sa.Numeric(7, 4), schema=target_schema)
    op.alter_column('reglas_impuestos', 'alicuota_defecto', type_=sa.Numeric(5, 2), existing_type=sa.Numeric(7, 4), schema=target_schema)
    op.alter_column('comprobantes_tributos', 'alicuota', type_=sa.Numeric(5, 2), existing_type=sa.Numeric(7, 4), schema=target_schema)

    # Reversión del casteo
    op.alter_column('periodos_contables', 'cerrado_por_id', type_=sa.Integer(), existing_type=sa.String(255), schema=target_schema, postgresql_using="cerrado_por_id::integer")

    # Eliminación del Constraint idempotente
    op.execute(f"ALTER TABLE {target_schema}.comprobantes DROP CONSTRAINT IF EXISTS chk_importe_total_positivo;")

    # Nota: No se hace un DROP automático de updated_at en el downgrade por seguridad de retención de trazas.