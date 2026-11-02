"""fix_auditable_mixin_idempotente

Revision ID: 1918f9f404b7
Revises: 8163dcf8c740
Create Date: 2026-04-24 12:51:19.987989

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1918f9f404b7'
down_revision: Union[str, None] = '8163dcf8c740'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    tablas_auditables = [
        'razones_sociales_propias', 'codigos_activacion', 'usuario_entidad_roles',
        'comprobantes', 'cuentas_bancarias', 'movimientos_bancarios',
        'logs_auditoria', 'reglas_aprendizaje', 'plan_cuentas',
        'asientos_contables', 'cola_mensajes_muertos', 'reglas_impuestos',
        'padrones_fiscales', 'historial_cotizaciones', 'webhook_subscriptions',
        'webhook_delivery_logs'
    ]

    # Ejecución de parche crudo idempotente (SQL Nativo v4.0)
    for tabla in tablas_auditables:
        op.execute(f"""
            ALTER TABLE {target_schema}.{tabla}
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;
        """)


def downgrade() -> None:
    # Por política de retención de datos, no hacemos DROP de columnas de auditoría.
    pass