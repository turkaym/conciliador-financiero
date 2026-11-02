"""crear_tabla_cola_mensajes_muertos

Revision ID: 0bff03d1f28e
Revises: 656e6300ca20
Create Date: 2026-05-20 13:42:23.307396

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0bff03d1f28e'
down_revision: Union[str, None] = '656e6300ca20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🛡️ ESCUDO DE IDEMPOTENCIA: Creación estructural segura usando SQL nativo
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS "{target_schema}".cola_mensajes_muertos (
            id SERIAL PRIMARY KEY,
            entidad_id INTEGER NOT NULL DEFAULT 1,
            punto_venta INTEGER,
            tipo_cbte_afip INTEGER,
            numero BIGINT,
            error_msg TEXT,
            traceback TEXT,
            resuelto BOOLEAN DEFAULT FALSE,
            resolved_by_id VARCHAR,
            resolved_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE
        );
    """)

def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 🛡️ ROLLBACK DEFENSIVO: Evita excepciones si la tabla no existe
    op.execute(f"""
        DROP TABLE IF EXISTS "{target_schema}".cola_mensajes_muertos CASCADE;
    """)