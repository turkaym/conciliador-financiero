from sqlalchemy import Column, Integer, BigInteger, String, Numeric, Date, Boolean, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB

from core.utils.enums import ClaseDocumento, AlicuotaIvaAFIP, TipoTributoAFIP
from core.database.models.mixins import TenantBase, AuditableMixin, prevent_financial_delete

class Comprobante(AuditableMixin, TenantBase):
    __tablename__ = "comprobantes"

    id = Column(Integer, primary_key=True, index=True)
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id"), nullable=False)
    entidad = relationship("RazonSocialPropia", back_populates="comprobantes")

    # 🌟 FIX FASE A: Enlace estricto con el Core Contable (Partida Doble)
    cuenta_contable_id = Column(Integer, ForeignKey("plan_cuentas.id"), nullable=True)

    tipo_operacion = Column(String(20), nullable=False, default="VENTA")
    clase_documento = Column(SQLEnum(ClaseDocumento, native_enum=False, length=50), nullable=False, default=ClaseDocumento.FACTURA)
    tipo_cbte_afip = Column(Integer, nullable=True)

    punto_venta = Column(Integer, nullable=False)
    numero = Column(BigInteger, nullable=False)
    fecha_emision = Column(Date, nullable=False, index=True)
    cuit_emisor = Column(String(11), nullable=False, index=True)
    cuit_receptor = Column(String(11), nullable=False, index=True)

    # Estructura Híbrida Multi-Alícuota (JSONB)
    importe_neto_gravado = Column(Numeric(18, 2), nullable=True, default=0.0)
    importe_no_gravado = Column(Numeric(18, 2), nullable=True, default=0.0)
    importe_exento = Column(Numeric(18, 2), nullable=True, default=0.0)

    subtotales_iva = Column(JSONB, nullable=True)
    otros_tributos = Column(JSONB, nullable=True)

    legacy_fiscal_data = Column(Boolean, default=False, nullable=False)

    # Columnas Legacy (A deprecar)
    importe_neto = Column(Numeric(15, 2), nullable=False, default=0.0)
    importe_iva = Column(Numeric(15, 2), nullable=False, default=0.0)
    importe_tributos = Column(Numeric(15, 2), nullable=False, default=0.0)
    importe_total = Column(Numeric(15, 2), nullable=False)

    saldo_pendiente = Column(Numeric(15, 2), nullable=False, default=0.0)
    es_saldo_a_favor = Column(Boolean, default=False, nullable=False)

    moneda = Column(String(3), default="ARS")
    cotizacion = Column(Numeric(15, 6), default=1.0, nullable=False)

    cae = Column(String(14), nullable=True)
    vencimiento_cae = Column(Date, nullable=True)
    estado = Column(String(50), default="BORRADOR", index=True)

    comprobante_origen_id = Column(Integer, ForeignKey('comprobantes.id'), nullable=True)
    documento_origen = relationship("Comprobante", remote_side=[id], backref="documentos_derivados")

    is_active = Column(Boolean, default=True, nullable=False)

    detalles_match = relationship("MatchDetalleComprobante", back_populates="comprobante")
    detalles_iva = relationship("ComprobanteIva", back_populates="comprobante", cascade="all, delete-orphan")
    detalles_tributos = relationship("ComprobanteTributo", back_populates="comprobante", cascade="all, delete-orphan")
    comprobantes_asociados = relationship("ComprobanteAsociado", foreign_keys="[ComprobanteAsociado.comprobante_id]", back_populates="comprobante_padre", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint('importe_total >= 0', name='chk_importe_total_positivo'),
        CheckConstraint('saldo_pendiente <= importe_total', name='chk_saldo_logico'), # 🌟 Escudo Matemático SQL
        Index('uix_comprobante_fiscal_unico_activo', 'cuit_emisor', 'tipo_cbte_afip', 'punto_venta', 'numero', unique=True, postgresql_where=(is_active == True), sqlite_where=(is_active == True)),
        Index('ix_comprobantes_iva_gin', 'subtotales_iva', postgresql_using='gin'),
        Index('ix_comprobantes_tributos_gin', 'otros_tributos', postgresql_using='gin')
    )

class ComprobanteIva(TenantBase):
    __tablename__ = "comprobantes_iva"

    id = Column(Integer, primary_key=True, index=True)
    comprobante_id = Column(Integer, ForeignKey("comprobantes.id", ondelete="CASCADE"), nullable=False)
    id_alicuota_afip = Column(SQLEnum(AlicuotaIvaAFIP, native_enum=False), nullable=False)
    base_imponible = Column(Numeric(15, 2), nullable=False, default=0.0)
    importe = Column(Numeric(15, 2), nullable=False, default=0.0)
    comprobante = relationship("Comprobante", back_populates="detalles_iva")

class ComprobanteTributo(TenantBase):
    __tablename__ = "comprobantes_tributos"

    id = Column(Integer, primary_key=True, index=True)
    comprobante_id = Column(Integer, ForeignKey("comprobantes.id", ondelete="CASCADE"), nullable=False)
    id_tributo_afip = Column(SQLEnum(TipoTributoAFIP, native_enum=False), nullable=False)
    descripcion = Column(String(255), nullable=True)
    base_imponible = Column(Numeric(15, 2), nullable=False, default=0.0)
    alicuota = Column(Numeric(7, 4), nullable=False, default=0.0)
    importe = Column(Numeric(15, 2), nullable=False, default=0.0)
    origen_alicuota = Column(String(50), nullable=True)
    id_regla_aplicada = Column(Integer, nullable=True)
    comprobante = relationship("Comprobante", back_populates="detalles_tributos")

class ComprobanteAsociado(TenantBase):
    __tablename__ = "comprobantes_asociados"

    id = Column(Integer, primary_key=True, index=True)
    comprobante_id = Column(Integer, ForeignKey("comprobantes.id", ondelete="CASCADE"), nullable=False)
    tipo_cbte_afip = Column(Integer, nullable=False)
    punto_venta = Column(Integer, nullable=False)
    numero = Column(Integer, nullable=False)
    cuit = Column(String(11), nullable=False)
    comprobante_vinculado_id = Column(Integer, ForeignKey("comprobantes.id", ondelete="SET NULL"), nullable=True)

    comprobante_padre = relationship("Comprobante", foreign_keys=[comprobante_id], back_populates="comprobantes_asociados")
    comprobante_vinculado = relationship("Comprobante", foreign_keys=[comprobante_vinculado_id])

# INMUTABILIDAD CONTABLE
event.listen(Comprobante, 'before_delete', prevent_financial_delete)