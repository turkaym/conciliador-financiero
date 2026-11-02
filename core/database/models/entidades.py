from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum

# 🌟 Asegúrate de que CondicionFiscalAFIP esté importado
from core.utils.enums import RolUsuario, CondicionFiscalAFIP
from core.database.models.mixins import TenantBase, AuditableMixin

# ==========================================
# ENTIDADES Y SEGURIDAD MULTI-TENANT
# ==========================================
class RazonSocialPropia(AuditableMixin, TenantBase):
    __tablename__ = "razones_sociales_propias"

    id = Column(Integer, primary_key=True, index=True)
    cuit = Column(String(11), unique=True, index=True, nullable=False)
    nombre_fantasia = Column(String(255), nullable=False)
    razon_social = Column(String(255), nullable=False)

    # 🌟 START FIX FASE 11: Inyección del Motor Fiscal Emisor
    condicion_fiscal = Column(SQLEnum(CondicionFiscalAFIP, native_enum=False, length=50), nullable=False, default=CondicionFiscalAFIP.NO_CATEGORIZADO)
    # 🌟 END FIX

    is_active = Column(Boolean, default=False, nullable=False)
    features = Column(JSON, default={}, nullable=False)

    # Bóveda AFIP
    afip_certificate = Column(Text, nullable=True)
    afip_private_key_encrypted = Column(Text, nullable=True)
    afip_cert_expiration = Column(DateTime(timezone=True), nullable=True)
    afip_last_sync_at = Column(DateTime(timezone=True), nullable=True)

    # Relaciones (Soft Strings)
    cuentas_bancarias = relationship("CuentaBancaria", back_populates="entidad")
    comprobantes = relationship("Comprobante", back_populates="entidad")
    roles_usuarios = relationship("UsuarioEntidadRol", back_populates="entidad", cascade="all, delete-orphan")
    reglas_aprendizaje = relationship("ReglaAprendizaje", back_populates="entidad", cascade="all, delete-orphan")
    reglas_impuestos = relationship("ReglaImpuesto", back_populates="entidad", cascade="all, delete-orphan")


class UsuarioEntidadRol(AuditableMixin, TenantBase):
    __tablename__ = "usuario_entidad_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id"), nullable=False)
    rol = Column(SQLEnum(RolUsuario, native_enum=False, length=50), nullable=False, default=RolUsuario.VISOR)

    entidad = relationship("RazonSocialPropia", back_populates="roles_usuarios")

    __table_args__ = (UniqueConstraint('user_id', 'entidad_id', name='uix_user_entidad_rol'),)


class ContactoComercial(AuditableMixin, TenantBase):
    """
    Maestro de Proveedores y Clientes (Entidades Externas B2B).
    """
    __tablename__ = "contactos_comerciales"

    id = Column(Integer, primary_key=True, index=True)
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id", ondelete="CASCADE"), nullable=False)
    cuit = Column(String(11), nullable=False, index=True)
    razon_social = Column(String(255), nullable=False)
    condicion_fiscal = Column(SQLEnum(CondicionFiscalAFIP, native_enum=False, length=50), nullable=False, default=CondicionFiscalAFIP.NO_CATEGORIZADO)
    cbu = Column(String(22), nullable=True)
    is_proveedor = Column(Boolean, default=True, nullable=False)
    is_cliente = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_entidad_financiera = Column(Boolean, default=False, nullable=False)

    entidad = relationship("RazonSocialPropia")

    __table_args__ = (
        UniqueConstraint('entidad_id', 'cuit', name='uix_entidad_cuit_contacto_activo'),
    )