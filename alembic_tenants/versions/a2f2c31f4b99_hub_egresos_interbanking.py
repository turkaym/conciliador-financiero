"""hub_egresos_interbanking

Revision ID: a2f2c31f4b99
Revises: cd9a9ac758f1
Create Date: 2026-05-31 02:26:32.118728

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2f2c31f4b99'
down_revision: Union[str, None] = 'cd9a9ac758f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    # 1. Maestro B2B: Contactos Comerciales
    op.create_table(
        'contactos_comerciales',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entidad_id', sa.Integer(), nullable=False),
        sa.Column('cuit', sa.String(length=11), nullable=False),
        sa.Column('razon_social', sa.String(length=255), nullable=False),
        sa.Column('cbu', sa.String(length=22), nullable=True),
        sa.Column('is_proveedor', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_cliente', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['entidad_id'], [f'{target_schema}.razones_sociales_propias.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entidad_id', 'cuit', name='uix_entidad_cuit_contacto_activo'),
        schema=target_schema
    )
    op.create_index('ix_contactos_comerciales_cuit', 'contactos_comerciales', ['cuit'], unique=False, schema=target_schema)
    op.create_index('ix_contactos_comerciales_id', 'contactos_comerciales', ['id'], unique=False, schema=target_schema)

    # 2. Taxonomía: Conceptos Operativos
    op.create_table(
        'conceptos_operativos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entidad_id', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(length=12), nullable=False),
        sa.Column('nombre_descriptivo', sa.String(length=100), nullable=False),
        sa.Column('requiere_comprobante_default', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['entidad_id'], [f'{target_schema}.razones_sociales_propias.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entidad_id', 'codigo', name='uix_entidad_codigo_concepto'),
        schema=target_schema
    )
    op.create_index('ix_conceptos_operativos_id', 'conceptos_operativos', ['id'], unique=False, schema=target_schema)

    # 3. Logística: Órdenes de Pago (Sifón Fiscal)
    op.create_table(
        'ordenes_pago',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entidad_id', sa.Integer(), nullable=False),
        sa.Column('codigo_trazabilidad', sa.String(length=32), nullable=False),
        sa.Column('concepto_id', sa.Integer(), nullable=False),
        sa.Column('proveedor_id', sa.Integer(), nullable=False),
        sa.Column('monto_estimado', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('moneda', sa.String(length=3), nullable=False),
        sa.Column('tipo_cambio_estimado', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('requiere_comprobante_fiscal', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('excluir_reportes_fiscales', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('comprobante_interno_url', sa.String(length=255), nullable=True),
        sa.Column('estado_orden', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['concepto_id'], [f'{target_schema}.conceptos_operativos.id'], ),
        sa.ForeignKeyConstraint(['entidad_id'], [f'{target_schema}.razones_sociales_propias.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['proveedor_id'], [f'{target_schema}.contactos_comerciales.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema=target_schema
    )
    op.create_index('ix_op_entidad_codigo', 'ordenes_pago', ['entidad_id', 'codigo_trazabilidad'], unique=True, schema=target_schema)
    op.create_index('ix_op_entidad_fecha', 'ordenes_pago', ['entidad_id', 'created_at'], unique=False, schema=target_schema)
    op.create_index('ix_ordenes_pago_id', 'ordenes_pago', ['id'], unique=False, schema=target_schema)

    # 4. Financiero: Lotes de Pago
    op.create_table(
        'lotes_pago',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entidad_id', sa.Integer(), nullable=False),
        sa.Column('codigo_lote', sa.String(length=32), nullable=False),
        sa.Column('moneda_pago', sa.String(length=3), nullable=False),
        sa.Column('monto_total_lote', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('estado_lote', sa.String(length=30), nullable=False),
        sa.Column('aprobado_por_id', sa.String(length=255), nullable=True),
        sa.Column('fecha_autorizacion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['entidad_id'], [f'{target_schema}.razones_sociales_propias.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema=target_schema
    )
    op.create_index('ix_lote_entidad_codigo', 'lotes_pago', ['entidad_id', 'codigo_lote'], unique=True, schema=target_schema)
    op.create_index('ix_lotes_pago_id', 'lotes_pago', ['id'], unique=False, schema=target_schema)

    # 5. Resolución: Detalles del Lote
    op.create_table(
        'lote_pago_detalles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lote_id', sa.Integer(), nullable=False),
        sa.Column('orden_pago_id', sa.Integer(), nullable=True),
        sa.Column('comprobante_id', sa.Integer(), nullable=True),
        sa.Column('monto_asignado_moneda_origen', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('monto_asignado_ars', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('tipo_cambio_aplicado', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.CheckConstraint('(comprobante_id IS NOT NULL OR orden_pago_id IS NOT NULL)', name='chk_lote_detalle_origen'),
        sa.ForeignKeyConstraint(['comprobante_id'], [f'{target_schema}.comprobantes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['lote_id'], [f'{target_schema}.lotes_pago.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['orden_pago_id'], [f'{target_schema}.ordenes_pago.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema=target_schema
    )
    op.create_index('ix_lote_pago_detalles_id', 'lote_pago_detalles', ['id'], unique=False, schema=target_schema)


def downgrade() -> None:
    # ROLLBACK DEFENSIVO: Resiliencia ante fallos parciales
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")

    op.execute(f"DROP TABLE IF EXISTS {target_schema}.lote_pago_detalles CASCADE;")
    op.execute(f"DROP TABLE IF EXISTS {target_schema}.lotes_pago CASCADE;")
    op.execute(f"DROP TABLE IF EXISTS {target_schema}.ordenes_pago CASCADE;")
    op.execute(f"DROP TABLE IF EXISTS {target_schema}.conceptos_operativos CASCADE;")
    op.execute(f"DROP TABLE IF EXISTS {target_schema}.contactos_comerciales CASCADE;")