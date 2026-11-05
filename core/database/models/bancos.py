from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Boolean, Float, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy import event
from sqlalchemy.sql import func

from core.database.models.mixins import TenantBase, AuditableMixin, prevent_financial_delete

# ==========================================
# BANCOS Y CONCILIACIÓN
# ==========================================
class CuentaBancaria(AuditableMixin, TenantBase):
    __tablename__ = "cuentas_bancarias"

    id = Column(Integer, primary_key=True, index=True)
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id"), nullable=True)
    proveedor_clearing_id = Column(Integer, ForeignKey("contactos_comerciales.id"), nullable=True)

    # 🌟 FIX ARQUITECTURA: Naturaleza del canal B2B
    tipo_canal = Column(String(50), nullable=False, default="BANCO")
    is_virtual_clearing = Column(Boolean, default=False, nullable=False)

    banco = Column(String(100), nullable=False)
    numero_cuenta = Column(String(50), nullable=False)
    cbu = Column(String(22), nullable=True)
    alias = Column(String(50), nullable=True)
    tipo_cuenta = Column(String(20), nullable=False, default="CC")
    moneda = Column(String(3), nullable=False, default="ARS")

    saldo_actual = Column(Numeric(18, 2), default=0.00, nullable=False)
    saldo_retenido = Column(Numeric(18, 2), default=0.00, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    is_syncing = Column(Boolean, default=False, nullable=False)
    last_task_id = Column(String(255), nullable=True)

    entidad = relationship("RazonSocialPropia", back_populates="cuentas_bancarias")
    movimientos = relationship("MovimientoBancario", back_populates="cuenta", cascade="all, delete-orphan")

    __table_args__ = (Index('ix_cuentas_syncing', 'is_syncing', postgresql_where=(is_syncing == True)),)

class MovimientoBancario(AuditableMixin, TenantBase):
    __tablename__ = "movimientos_bancarios"

    id = Column(Integer, primary_key=True, index=True)
    cuenta_id = Column(Integer, ForeignKey("cuentas_bancarias.id"), nullable=False)

    usuario_creador_id = Column(String(50), nullable=False, index=True)
    usuario_resolutor_id = Column(String(50), nullable=True, index=True)
    motivo_rechazo = Column(Text, nullable=True)

    referencia_banco = Column(String(100), nullable=True, index=True)
    hash_transaccional = Column(String(64), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)

    concepto_bancario_crudo = Column(String(255), nullable=False)
    concepto_interno = Column(String(255), nullable=True)

    monto = Column(Numeric(18, 2), nullable=False, index=True)
    saldo_pendiente = Column(Numeric(18, 2), nullable=False, default=0.00)
    saldo_resultante = Column(Numeric(18, 2), nullable=True)

    anulado = Column(Boolean, default=False, nullable=False)
    estado = Column(String(50), default="APROBADO", index=True)

    cuenta = relationship("CuentaBancaria", back_populates="movimientos")
    # 🌟 FIX ARQUITECTURA: Se elimina 'detalles_match' de aquí. La conciliación ya no interactúa con esta tabla deprecada.

    __table_args__ = (
        UniqueConstraint('cuenta_id', 'hash_transaccional', name='uix_movimiento_unico_hash'),
        Index('ix_mov_concepto_trgm', 'concepto_bancario_crudo', postgresql_using='gin', postgresql_ops={'concepto_bancario_crudo': 'gin_trgm_ops'}),
    )

class ConciliacionMatch(TenantBase):
    __tablename__ = "conciliacion_matches"

    id = Column(Integer, primary_key=True, index=True)
    score = Column(Float, default=1.0)
    metodo = Column(String(50), default="exact_amount_date")
    fecha_match = Column(DateTime(timezone=True), server_default=func.now())

    is_active = Column(Boolean, default=True, nullable=False, server_default="true")

    detalles_comprobantes = relationship("MatchDetalleComprobante", back_populates="match", cascade="all, delete-orphan")
    detalles_movimientos = relationship("MatchDetalleMovimiento", back_populates="match", cascade="all, delete-orphan")
    asientos = relationship("AsientoContable", back_populates="match")

class MatchDetalleComprobante(TenantBase):
    __tablename__ = "match_detalle_comprobantes"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("conciliacion_matches.id", ondelete="CASCADE"), nullable=False)
    comprobante_id = Column(Integer, ForeignKey("comprobantes.id", ondelete="CASCADE"), nullable=False)
    monto_aplicado = Column(Numeric(15, 2), nullable=False)

    match = relationship("ConciliacionMatch", back_populates="detalles_comprobantes")
    comprobante = relationship("Comprobante", back_populates="detalles_match")

class MatchDetalleMovimiento(TenantBase):
    __tablename__ = "match_detalle_movimientos"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("conciliacion_matches.id", ondelete="CASCADE"), nullable=False)

    # 🌟 FIX ARQUITECTURA: Reestructuración de la Clave Foránea hacia el Ledger Unificado de Tesorería
    movimiento_tesoreria_id = Column(Integer, ForeignKey("movimientos_tesoreria.id", ondelete="CASCADE"), nullable=False)
    monto_aplicado = Column(Numeric(15, 2), nullable=False)

    match = relationship("ConciliacionMatch", back_populates="detalles_movimientos")
    movimiento_tesoreria = relationship("MovimientoTesoreria", back_populates="detalles_match")

# INMUTABILIDAD CONTABLE
event.listen(MovimientoBancario, 'before_delete', prevent_financial_delete)