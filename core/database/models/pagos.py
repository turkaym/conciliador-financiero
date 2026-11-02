from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, ForeignKey, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum

from core.utils.enums import MonedaISO, EstadoOrdenPago, EstadoLotePago
from core.database.models.mixins import TenantBase, AuditableMixin

# ==========================================
# HUB DE EGRESOS, LOTES E INTERBANKING
# ==========================================
class ConceptoOperativo(AuditableMixin, TenantBase):
    __tablename__ = "conceptos_operativos"

    id = Column(Integer, primary_key=True, index=True)
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id", ondelete="CASCADE"), nullable=False)
    codigo = Column(String(12), nullable=False)
    nombre_descriptivo = Column(String(100), nullable=False)
    requiere_comprobante_default = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    entidad = relationship("RazonSocialPropia")

    __table_args__ = (UniqueConstraint('entidad_id', 'codigo', name='uix_entidad_codigo_concepto'),)

class OrdenPago(AuditableMixin, TenantBase):
    __tablename__ = "ordenes_pago"

    id = Column(Integer, primary_key=True, index=True)
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id", ondelete="CASCADE"), nullable=False)

    creado_por_id = Column(String(50), nullable=True)
    actualizado_por_id = Column(String(50), nullable=True)
    codigo_trazabilidad = Column(String(32), nullable=False)
    concepto_id = Column(Integer, ForeignKey("conceptos_operativos.id"), nullable=False)
    proveedor_id = Column(Integer, ForeignKey("contactos_comerciales.id"), nullable=False)

    monto_estimado = Column(Numeric(18, 2), nullable=False)
    moneda = Column(SQLEnum(MonedaISO, native_enum=False, length=3), nullable=False, default=MonedaISO.ARS)
    tipo_cambio_estimado = Column(Numeric(10, 4), nullable=False, default=1.0)

    requiere_comprobante_fiscal = Column(Boolean, default=True, nullable=False)
    excluir_reportes_fiscales = Column(Boolean, default=False, nullable=False)
    comprobante_interno_url = Column(String(255), nullable=True)
    estado_orden = Column(SQLEnum(EstadoOrdenPago, native_enum=False, length=30), nullable=False, default=EstadoOrdenPago.BORRADOR)

    entidad = relationship("RazonSocialPropia")
    concepto = relationship("ConceptoOperativo")
    proveedor = relationship("ContactoComercial")

    __table_args__ = (
        Index('ix_op_entidad_codigo', 'entidad_id', 'codigo_trazabilidad', unique=True),
        Index('ix_op_entidad_fecha', 'entidad_id', 'created_at'),
    )

class LotePago(AuditableMixin, TenantBase):
    __tablename__ = "lotes_pago"

    id = Column(Integer, primary_key=True, index=True)
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id", ondelete="CASCADE"), nullable=False)

    # 🌟 BIG BANG CUT-OVER: Extirpación de Bancos Legacy. Enlace directo y exclusivo a Tesorería.
    cuenta_tesoreria_id = Column(Integer, ForeignKey("cuentas_tesoreria.id"), nullable=True)

    creado_por_id = Column(String(50), nullable=True)
    actualizado_por_id = Column(String(50), nullable=True)
    codigo_lote = Column(String(32), nullable=False)
    moneda_pago = Column(SQLEnum(MonedaISO, native_enum=False, length=3), nullable=False, default=MonedaISO.ARS)
    monto_total_lote = Column(Numeric(18, 2), nullable=False)

    estado_lote = Column(SQLEnum(EstadoLotePago, native_enum=False, length=30), nullable=False, default=EstadoLotePago.DRAFT)

    aprobado_por_id = Column(String(255), nullable=True)
    fecha_autorizacion = Column(DateTime(timezone=True), nullable=True)

    entidad = relationship("RazonSocialPropia")
    detalles = relationship("LotePagoDetalle", back_populates="lote", cascade="all, delete-orphan")

    # 🌟 Relación ORM apuntando exclusivamente a la nueva arquitectura
    cuenta_tesoreria = relationship("CuentaTesoreria")

    __table_args__ = (Index('ix_lote_entidad_codigo', 'entidad_id', 'codigo_lote', unique=True),)

class LotePagoDetalle(TenantBase):
    __tablename__ = "lote_pago_detalles"

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes_pago.id", ondelete="CASCADE"), nullable=True)

    creado_por_id = Column(String(50), nullable=True)
    actualizado_por_id = Column(String(50), nullable=True)
    orden_pago_id = Column(Integer, ForeignKey("ordenes_pago.id", ondelete="SET NULL"), nullable=True)
    comprobante_id = Column(Integer, ForeignKey("comprobantes.id", ondelete="SET NULL"), nullable=True)

    monto_asignado_moneda_origen = Column(Numeric(18, 2), nullable=False)
    monto_asignado_ars = Column(Numeric(18, 2), nullable=False)
    tipo_cambio_aplicado = Column(Numeric(10, 4), nullable=False, default=1.0)

    lote = relationship("LotePago", back_populates="detalles")
    orden_pago = relationship("OrdenPago")
    comprobante = relationship("Comprobante")

    __table_args__ = (
        CheckConstraint("(comprobante_id IS NOT NULL OR orden_pago_id IS NOT NULL)", name='chk_lote_detalle_origen'),
    )