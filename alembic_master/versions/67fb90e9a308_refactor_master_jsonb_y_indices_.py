"""refactor_master_jsonb_y_indices_parciales

Revision ID: 67fb90e9a308
Revises: 871d2ddf9f9b
Create Date: 2026-05-27 22:35:54.104968

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '67fb90e9a308'
down_revision: Union[str, None] = '871d2ddf9f9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Casteos nativos explícitos (USING) para evitar bloqueos por tipo de dato en producción
    op.alter_column('audit_trail', 'changes',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_nullable=True,
               postgresql_using='changes::jsonb')

    op.alter_column('tenants', 'enabled_modules',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_nullable=True,
               postgresql_using='enabled_modules::jsonb')

    op.alter_column('tenants', 'settings',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_nullable=True,
               postgresql_using='settings::jsonb')

    op.alter_column('tenants', 'features',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_nullable=True,
               existing_server_default=sa.text("'{}'::json"),
               postgresql_using='features::jsonb')

    # Reconstrucción de Foreign Keys con nombres explícitos para preservar idempotencia en rollbacks
    op.drop_constraint('audit_trail_tenant_id_fkey', 'audit_trail', type_='foreignkey')
    op.drop_constraint('audit_trail_user_id_fkey', 'audit_trail', type_='foreignkey')
    op.create_foreign_key('audit_trail_user_id_fkey', 'audit_trail', 'users', ['user_id'], ['id'], source_schema='public', referent_schema='public', ondelete='SET NULL')
    op.create_foreign_key('audit_trail_tenant_id_fkey', 'audit_trail', 'tenants', ['tenant_id'], ['id'], source_schema='public', referent_schema='public', ondelete='CASCADE')

    op.drop_constraint('users_tenant_id_fkey', 'users', type_='foreignkey')
    op.create_foreign_key('users_tenant_id_fkey', 'users', 'tenants', ['tenant_id'], ['id'], source_schema='public', referent_schema='public', ondelete='CASCADE')

    # Generación de Índices de Telemetría
    op.create_index(op.f('ix_public_system_logs_created_at'), 'system_logs', ['created_at'], unique=False, schema='public')
    op.create_index(op.f('ix_public_system_logs_level'), 'system_logs', ['level'], unique=False, schema='public')
    op.create_index(op.f('ix_public_system_logs_module'), 'system_logs', ['module'], unique=False, schema='public')
    op.create_index(op.f('ix_public_system_logs_tenant_reference'), 'system_logs', ['tenant_reference'], unique=False, schema='public')

    # Transición de restricciones a Índices Parciales (Zero-Collision Soft Delete)
    op.drop_constraint('tenants_schema_name_key', 'tenants', type_='unique')
    op.drop_index('ix_public_tenants_cuit', table_name='tenants')
    op.create_index(op.f('ix_public_tenants_cuit'), 'tenants', ['cuit'], unique=False, schema='public')
    op.create_index('ix_tenants_cuit_active', 'tenants', ['cuit'], unique=True, schema='public', postgresql_where=sa.text('is_active = true'))
    op.create_index('ix_tenants_schema_active', 'tenants', ['schema_name'], unique=True, schema='public', postgresql_where=sa.text('is_active = true'))

    op.drop_index('ix_public_users_email', table_name='users')
    op.create_index(op.f('ix_public_users_email'), 'users', ['email'], unique=False, schema='public')
    op.create_index('ix_users_email_active', 'users', ['email'], unique=True, schema='public', postgresql_where=sa.text('is_active = true'))


def downgrade() -> None:
    op.drop_constraint('users_tenant_id_fkey', 'users', schema='public', type_='foreignkey')
    op.create_foreign_key('users_tenant_id_fkey', 'users', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')

    op.drop_index('ix_users_email_active', table_name='users', schema='public', postgresql_where=sa.text('is_active = true'))
    op.drop_index(op.f('ix_public_users_email'), table_name='users', schema='public')
    op.create_index('ix_public_users_email', 'users', ['email'], unique=True)

    op.drop_index('ix_tenants_schema_active', table_name='tenants', schema='public', postgresql_where=sa.text('is_active = true'))
    op.drop_index('ix_tenants_cuit_active', table_name='tenants', schema='public', postgresql_where=sa.text('is_active = true'))
    op.drop_index(op.f('ix_public_tenants_cuit'), table_name='tenants', schema='public')
    op.create_index('ix_public_tenants_cuit', 'tenants', ['cuit'], unique=True)
    op.create_unique_constraint('tenants_schema_name_key', 'tenants', ['schema_name'])

    op.alter_column('tenants', 'features',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_nullable=True,
               existing_server_default=sa.text("'{}'::json"),
               postgresql_using='features::json')
    op.alter_column('tenants', 'settings',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_nullable=True,
               postgresql_using='settings::json')
    op.alter_column('tenants', 'enabled_modules',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_nullable=True,
               postgresql_using='enabled_modules::json')

    op.drop_index(op.f('ix_public_system_logs_tenant_reference'), table_name='system_logs', schema='public')
    op.drop_index(op.f('ix_public_system_logs_module'), table_name='system_logs', schema='public')
    op.drop_index(op.f('ix_public_system_logs_level'), table_name='system_logs', schema='public')
    op.drop_index(op.f('ix_public_system_logs_created_at'), table_name='system_logs', schema='public')

    op.drop_constraint('audit_trail_user_id_fkey', 'audit_trail', schema='public', type_='foreignkey')
    op.drop_constraint('audit_trail_tenant_id_fkey', 'audit_trail', schema='public', type_='foreignkey')
    op.create_foreign_key('audit_trail_user_id_fkey', 'audit_trail', 'users', ['user_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('audit_trail_tenant_id_fkey', 'audit_trail', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')

    op.alter_column('audit_trail', 'changes',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_nullable=True,
               postgresql_using='changes::json')