"""fase_b_refactor_nm_gin

Revision ID: <AQUI_DEJA_EL_ID_QUE_GENERO_ALEMBIC>
Revises: 5185914a5c5d
Create Date: 2026-04-21 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1140065f9e15'
down_revision: Union[str, None] = '5185914a5c5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")
    if not target_schema:
        raise ValueError("Es obligatorio proveer 'tenant_schema'.")

    # 1. Renombrar la columna (Preserva los datos existentes)
    op.alter_column('movimientos_bancarios', 'concepto', new_column_name='concepto_bancario_crudo', schema=target_schema)

    # 2. Agregar la nueva columna de concepto interno mutable
    op.add_column('movimientos_bancarios', sa.Column('concepto_interno', sa.String(length=255), nullable=True), schema=target_schema)

    # 3. Recrear el índice GIN de búsqueda difusa apuntando a la nueva columna
    op.drop_index('ix_mov_concepto_trgm', table_name='movimientos_bancarios', schema=target_schema)
    op.create_index(
        'ix_mov_concepto_trgm',
        'movimientos_bancarios',
        ['concepto_bancario_crudo'],
        unique=False,
        schema=target_schema,
        postgresql_using='gin',
        postgresql_ops={'concepto_bancario_crudo': 'gin_trgm_ops'}
    )


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")
    if not target_schema:
        raise ValueError("Es obligatorio proveer 'tenant_schema'.")

    # Reversión exacta
    op.drop_index('ix_mov_concepto_trgm', table_name='movimientos_bancarios', schema=target_schema)
    op.drop_column('movimientos_bancarios', 'concepto_interno', schema=target_schema)
    op.alter_column('movimientos_bancarios', 'concepto_bancario_crudo', new_column_name='concepto', schema=target_schema)
    op.create_index(
        'ix_mov_concepto_trgm',
        'movimientos_bancarios',
        ['concepto'],
        unique=False,
        schema=target_schema,
        postgresql_using='gin',
        postgresql_ops={'concepto': 'gin_trgm_ops'}
    )