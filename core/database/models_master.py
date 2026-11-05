from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database.base import Base

class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        # 🛡️ FIX ARQUITECTURA: Índices Parciales
        Index('ix_tenants_cuit_active', 'cuit', unique=True, postgresql_where=Column('is_active') == True),
        Index('ix_tenants_schema_active', 'schema_name', unique=True, postgresql_where=Column('is_active') == True),
        {'schema': 'public'}
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    cuit = Column(String(11), nullable=False, index=True)
    schema_name = Column(String, nullable=False)

    is_active = Column(Boolean, default=True)

    # ==========================================
    # 💳 FASE 10: GOBERNANZA B2B Y FACTURACIÓN
    # ==========================================
    billing_provider = Column(String(50), nullable=True) # ej: 'STRIPE', 'MERCADOPAGO', 'NONE'
    provider_customer_id = Column(String(100), nullable=True, index=True) # cus_123456789
    subscription_status = Column(String(50), default="trialing", server_default="'trialing'") # active, past_due, canceled
    current_period_end = Column(DateTime(timezone=True), nullable=True)

    # 🛡️ GOD MODE BYPASS: Si es True, ignora el subscription_status y otorga acceso total
    manual_subscription_bypass = Column(Boolean, default=False, server_default='false')
    # ==========================================

    # ⚡ FIX PERFORMANCE: Transición a JSONB Nativo de PostgreSQL
    enabled_modules = Column(JSONB, default=lambda: ["arca_billing"])
    settings = Column(JSONB, default=dict)
    features = Column(JSONB, default=dict, server_default='{}')

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # 🛡️ FIX ARQUITECTURA: Unicidad de Email solo para cuentas activas
        Index('ix_users_email_active', 'email', unique=True, postgresql_where=Column('is_active') == True),
        {'schema': 'public'}
    )

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)

    role = Column(String, default="operator")

    status = Column(String, default="PENDING_EMAIL_VERIFICATION", server_default="'PENDING_EMAIL_VERIFICATION'")
    is_active = Column(Boolean, default=True)

    tenant_id = Column(Integer, ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False)
    tenant = relationship("Tenant", back_populates="users")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SystemLog(Base):
    __tablename__ = "system_logs"
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String, default="ERROR", index=True)  # ⚡ Indexado para queries de monitoreo rápido
    module = Column(String, nullable=False, index=True)
    message = Column(String, nullable=False)
    details = Column(String, nullable=True)
    tenant_reference = Column(String, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class AuditTrail(Base):
    """
    Tabla Inmutable de Trazabilidad Criptográfica.
    """
    __tablename__ = "audit_trail"
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=True, index=True)

    user_id = Column(Integer, ForeignKey("public.users.id", ondelete="SET NULL"), nullable=True, index=True)

    action = Column(String(50), nullable=False, index=True)
    entity_name = Column(String(100), nullable=False, index=True)
    entity_id = Column(String, nullable=True)

    ip_address = Column(String(50), nullable=True)
    changes = Column(JSONB, nullable=True) # ⚡ Transición a JSONB

    hash_firma = Column(String(64), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", lazy="selectin")
    tenant = relationship("Tenant", lazy="selectin")