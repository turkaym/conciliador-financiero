"""fase_c_b2b_webhooks

Revision ID: fef62fbaaf45
Revises: 1140065f9e15
Create Date: 2026-04-21 19:09:46.263320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fef62fbaaf45'
down_revision: Union[str, None] = '1140065f9e15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")
    if not target_schema:
        raise ValueError("Es obligatorio proveer 'tenant_schema'.")

    # 1. Tabla de API Keys
    op.create_table('api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entidad_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('prefix', sa.String(length=8), nullable=False),
        sa.Column('hashed_key', sa.String(length=128), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['entidad_id'], [f'{target_schema}.razones_sociales_propias.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema=target_schema
    )
    op.create_index(op.f('ix_api_keys_id'), 'api_keys', ['id'], unique=False, schema=target_schema)
    op.create_index(op.f('ix_api_keys_prefix'), 'api_keys', ['prefix'], unique=True, schema=target_schema)

    # 2. Tabla de Suscripciones Webhook
    op.create_table('webhook_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entidad_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('event_types', sa.JSON(), nullable=False),
        sa.Column('secret', sa.String(length=128), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['entidad_id'], [f'{target_schema}.razones_sociales_propias.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema=target_schema
    )
    op.create_index(op.f('ix_webhook_subscriptions_id'), 'webhook_subscriptions', ['id'], unique=False, schema=target_schema)

    # 3. Tabla de Logs de Evidencia (Delivery Logs)
    op.create_table('webhook_delivery_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('is_successful', sa.Boolean(), nullable=False, default=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False, default=1),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['subscription_id'], [f'{target_schema}.webhook_subscriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema=target_schema
    )
    op.create_index(op.f('ix_webhook_delivery_logs_event_id'), 'webhook_delivery_logs', ['event_id'], unique=False, schema=target_schema)
    op.create_index(op.f('ix_webhook_delivery_logs_id'), 'webhook_delivery_logs', ['id'], unique=False, schema=target_schema)


def downgrade() -> None:
    context = op.get_context()
    target_schema = context.config.attributes.get("tenant_schema") or context.opts.get("tenant_schema")
    if not target_schema:
        raise ValueError("Es obligatorio proveer 'tenant_schema'.")

    op.drop_table('webhook_delivery_logs', schema=target_schema)
    op.drop_table('webhook_subscriptions', schema=target_schema)
    op.drop_table('api_keys', schema=target_schema)