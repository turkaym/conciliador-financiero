from sqlalchemy import Column, Integer, String, Numeric, Date, Boolean, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import event

from core.database.models.mixins import TenantBase, AuditableMixin, prevent_financial_delete
from core.utils.enums import TipoCuentaTesoreria, TipoMovimientoTesoreria, MonedaISO
from core.database.models.contabilidad import AsientoContable

class CuentaTesoreria(AuditableMixin, TenantBase):
    __tablename__ = "cuentas_tesoreria"

    id = Column(Integer, primary_key=True, index=True)
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id"), nullable=False)
    proveedor_clearing_id = Column(Integer, ForeignKey("contactos_comerciales.id"), nullable=True)
    cuenta_contable_id = Column(Integer, ForeignKey("plan_cuentas.id"), nullable=True)
    nombre = Column(String(100), nullable=False)
    tipo_cuenta = Column(SQLEnum(TipoCuentaTesoreria, native_enum=False, length=30), nullable=False)
    moneda = Column(SQLEnum(MonedaISO, native_enum=False, length=3), nullable=False, default=MonedaISO.ARS)

    cbu_cvu = Column(String(22), nullable=True)
    alias = Column(String(50), nullable=True)
    numero_cuenta = Column(String(50), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    is_virtual_clearing = Column(Boolean, default=False, nullable=False)
    is_default_cash = Column(Boolean, default=False, nullable=False)
    is_syncing = Column(Boolean, default=False, nullable=False)
    last_task_id = Column(String(255), nullable=True)

    saldo_actual = Column(Numeric(15, 2), default=0.00, nullable=False)

    entidad = relationship("RazonSocialPropia")
    proveedor_clearing = relationship("ContactoComercial")
    movimientos = relationship("MovimientoTesoreria", back_populates="cuenta", cascade="all, delete-orphan")
    solicitudes = relationship("SolicitudMovimientoTesoreria", back_populates="cuenta", cascade="all, delete-orphan")

class MovimientoTesoreria(AuditableMixin, TenantBase):
    __tablename__ = "movimientos_tesoreria"

    id = Column(Integer, primary_key=True, index=True)
    cuenta_id = Column(Integer, ForeignKey("cuentas_tesoreria.id"), nullable=False)

    tipo = Column(SQLEnum(TipoMovimientoTesoreria, native_enum=False, length=20), nullable=False)
    fecha = Column(Date, nullable=False, index=True)
    monto = Column(Numeric(18, 2), nullable=False)
    moneda = Column(SQLEnum(MonedaISO, native_enum=False, length=3), nullable=False, default=MonedaISO.ARS)

    # 🌟 CONFIGURACIÓN ENTERPRISE: Control de saldos remanentes e inmutabilidad contable
    saldo_pendiente = Column(Numeric(18, 2), nullable=False, index=True)
    saldo_resultante = Column(Numeric(18, 2), nullable=True)

    concepto_crudo = Column(String(255), nullable=False)
    referencia_externa = Column(String(100), nullable=True, index=True)
    hash_transaccional = Column(String(64), nullable=False, index=True)

    comprobante_id = Column(Integer, ForeignKey("comprobantes.id", ondelete="SET NULL"), nullable=True)

    # 🌟 FIX: Trazabilidad bidireccional con Contabilidad
    asiento_id = Column(Integer, ForeignKey("asientos_contables.id", ondelete="SET NULL"), nullable=True)

    anulado = Column(Boolean, default=False, nullable=False)
    motivo_anulacion = Column(Text, nullable=True)

    cuenta = relationship("CuentaTesoreria", back_populates="movimientos")
    comprobante = relationship("Comprobante")

    asiento_contable = relationship("AsientoContable")

    detalles_match = relationship("MatchDetalleMovimiento", back_populates="movimiento_tesoreria")

    __table_args__ = (
        UniqueConstraint('cuenta_id', 'hash_transaccional', name='uix_mov_tesoreria_unico_hash'),
        Index('ix_mov_tesoreria_busqueda', 'concepto_crudo', postgresql_using='gin', postgresql_ops={'concepto_crudo': 'gin_trgm_ops'}),
    )

class SolicitudMovimientoTesoreria(AuditableMixin, TenantBase):
    __tablename__ = "solicitudes_movimientos_tesoreria"

    id = Column(Integer, primary_key=True, index=True)
    cuenta_id = Column(Integer, ForeignKey("cuentas_tesoreria.id", ondelete="CASCADE"), nullable=False)

    tipo = Column(SQLEnum(TipoMovimientoTesoreria, native_enum=False, length=20), nullable=False)
    fecha = Column(Date, nullable=False, index=True)
    monto = Column(Numeric(18, 2), nullable=False)
    moneda = Column(SQLEnum(MonedaISO, native_enum=False, length=3), nullable=False, default=MonedaISO.ARS)

    concepto_crudo = Column(String(255), nullable=False)
    referencia_externa = Column(String(100), nullable=True, index=True)
    hash_transaccional = Column(String(64), nullable=False, index=True)

    estado = Column(String(30), nullable=False, default="PENDING_APPROVAL")
    usuario_resolutor_id = Column(String(50), nullable=True)
    motivo_rechazo = Column(Text, nullable=True)

    movimiento_definitivo_id = Column(Integer, ForeignKey("movimientos_tesoreria.id", ondelete="SET NULL"), nullable=True)

    cuenta = relationship("CuentaTesoreria", back_populates="solicitudes")
    movimiento_definitivo = relationship("MovimientoTesoreria")

# 🌟 HOOK ORM: Sincronización automática del Saldo Pendiente inicial al insertar un registro
@event.listens_for(MovimientoTesoreria, 'before_insert')
def asignar_saldo_pendiente_inicial(mapper, connection, target):
    if target.monto is not None:
        target.saldo_pendiente = abs(target.monto)

event.listen(MovimientoTesoreria, 'before_delete', prevent_financial_delete)
event.listen(SolicitudMovimientoTesoreria, 'before_delete', prevent_financial_delete)