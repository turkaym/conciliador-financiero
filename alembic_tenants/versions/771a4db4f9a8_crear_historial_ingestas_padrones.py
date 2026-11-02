"""crear_historial_ingestas_padrones

Revision ID: 771a4db4f9a8
Revises: 2b27979a6f0d
Create Date: 2026-07-05 14:30:43.488194

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '771a4db4f9a8'
down_revision: Union[str, None] = '2b27979a6f0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🌟 DDL Defensivo: Creación de tabla idempotente
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {target_schema}.historial_ingestas_padrones (
            id SERIAL PRIMARY KEY,
            entidad_id INTEGER NOT NULL,
            jurisdiccion VARCHAR(50) NOT NULL,
            periodo VARCHAR(6) NOT NULL,
            nombre_archivo VARCHAR(255) NOT NULL,
            estado VARCHAR(20) DEFAULT 'PROCESANDO' NOT NULL,
            registros_insertados INTEGER DEFAULT 0 NOT NULL,
            mensaje_error TEXT,
            tarea_celery_id VARCHAR(255),
            iniciado_el TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            finalizado_el TIMESTAMP WITH TIME ZONE,

            -- Campos AuditableMixin
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            created_by VARCHAR(255),
            updated_by VARCHAR(255),

            CONSTRAINT fk_hist_padrones_entidad FOREIGN KEY (entidad_id)
                REFERENCES {target_schema}.razones_sociales_propias(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS ix_historial_padrones_jurisdiccion
            ON {target_schema}.historial_ingestas_padrones (jurisdiccion);

        CREATE INDEX IF NOT EXISTS ix_historial_padrones_periodo
            ON {target_schema}.historial_ingestas_padrones (periodo);

        CREATE INDEX IF NOT EXISTS ix_historial_padrones_tarea
            ON {target_schema}.historial_ingestas_padrones (tarea_celery_id);
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🌟 Downgrade Defensivo: Eliminación limpia
    op.execute(f"DROP INDEX IF EXISTS {target_schema}.ix_historial_padrones_tarea;")
    op.execute(f"DROP INDEX IF EXISTS {target_schema}.ix_historial_padrones_periodo;")
    op.execute(f"DROP INDEX IF EXISTS {target_schema}.ix_historial_padrones_jurisdiccion;")
    op.execute(f"DROP TABLE IF EXISTS {target_schema}.historial_ingestas_padrones CASCADE;")