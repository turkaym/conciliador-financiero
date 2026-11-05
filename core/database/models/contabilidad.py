from sqlalchemy import Column, Integer, String, Boolean, Numeric, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from sqlalchemy import event

from core.database.models.mixins import TenantBase, AuditableMixin, prevent_financial_delete

# ==========================================
# CONTABILIDAD GENERAL Y AUDITORÍA
# ==========================================
class ReglaAprendizaje(AuditableMixin, TenantBase):
    __tablename__ = "reglas_aprendizaje"

    id = Column(Integer, primary_key=True, index=True)
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id"), nullable=False)
    patron_concepto = Column(String(255), nullable=False, index=True)
    cuit_asociado = Column(String(11), nullable=True)
    tipo_cbte_asociado = Column(Integer, nullable=True)
    frecuencia_uso = Column(Integer, default=1)
    activa = Column(Boolean, default=True)

    entidad = relationship("RazonSocialPropia", back_populates="reglas_aprendizaje")

class ReglaImpuesto(AuditableMixin, TenantBase):
    __tablename__ = "reglas_impuestos"

    id = Column(Integer, primary_key=True, index=True)
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id"), nullable=False)
    tipo_impuesto = Column(String(50), nullable=False, index=True)
    jurisdiccion = Column(String(50), nullable=False)

    codigo_regimen_afip = Column(Integer, nullable=False, default=217)
    alicuota_defecto = Column(Numeric(5, 2), nullable=False)
    monto_minimo_sujeto = Column(Numeric(15, 2), nullable=False, default=0.0)
    aplica_padron = Column(Boolean, default=False)
    cuenta_contable_id = Column(Integer, ForeignKey("plan_cuentas.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    entidad = relationship("RazonSocialPropia", back_populates="reglas_impuestos")
    cuenta_contable = relationship("PlanCuentas")

    __table_args__ = (UniqueConstraint('entidad_id', 'tipo_impuesto', 'jurisdiccion', name='uix_regla_impuesto_entidad'),)

class PlanCuentas(AuditableMixin, TenantBase):
    __tablename__ = "plan_cuentas"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), nullable=False, unique=True, index=True)
    nombre = Column(String(255), nullable=False)
    codigo_sistema = Column(String(50), unique=True, nullable=True, index=True)
    is_system = Column(Boolean, default=False)
    tipo = Column(String(50), nullable=False)
    imputable = Column(Boolean, default=False, nullable=False)
    parent_id = Column(Integer, ForeignKey("plan_cuentas.id"), nullable=True)

    subcuentas = relationship("PlanCuentas", backref=backref('parent', remote_side=[id]))

class AsientoContable(AuditableMixin, TenantBase):
    __tablename__ = "asientos_contables"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False, index=True)
    concepto = Column(String(255), nullable=False)
    match_id = Column(Integer, ForeignKey("conciliacion_matches.id", ondelete="SET NULL"), nullable=True)

    # 🌟 FIX ENTERPRISE: Relación recursiva para Asientos de Extorno (Inmutabilidad del Ledger)
    estado = Column(String(20), default="VIGENTE", nullable=False) # VIGENTE, EXTORNO, REVERTIDO
    asiento_revertido_id = Column(Integer, ForeignKey("asientos_contables.id"), nullable=True)
    asiento_revertido = relationship("AsientoContable", remote_side=[id], backref="extornos")

    match = relationship("ConciliacionMatch", back_populates="asientos")
    lineas = relationship("LineaAsiento", back_populates="asiento", cascade="all, delete-orphan")

class LineaAsiento(TenantBase):
    __tablename__ = "lineas_asiento"
    id = Column(Integer, primary_key=True, index=True)
    asiento_id = Column(Integer, ForeignKey("asientos_contables.id"), nullable=False)
    cuenta_id = Column(Integer, ForeignKey("plan_cuentas.id"), nullable=False)
    debe = Column(Numeric(15, 2), default=0.0, nullable=False)
    haber = Column(Numeric(15, 2), default=0.0, nullable=False)

    asiento = relationship("AsientoContable", back_populates="lineas")
    cuenta = relationship("PlanCuentas")

class PeriodoContable(TenantBase):
    __tablename__ = "periodos_contables"

    id = Column(Integer, primary_key=True, index=True)
    anio = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    estado = Column(String, default="CERRADO")
    cerrado_el = Column(DateTime(timezone=True), server_default=func.now())
    cerrado_por_id = Column(String(255), nullable=True)

    __table_args__ = (UniqueConstraint('anio', 'mes', name='uq_periodo_anio_mes'),)

class HistorialCotizacion(AuditableMixin, TenantBase):
    __tablename__ = "historial_cotizaciones"

    id = Column(Integer, primary_key=True, index=True)
    moneda = Column(String(3), nullable=False)
    fecha = Column(Date, nullable=False, index=True)
    cotizacion_compra = Column(Numeric(15, 6), nullable=False)
    cotizacion_venta = Column(Numeric(15, 6), nullable=False)
    origen = Column(String(50), nullable=False, default="BNA")

    __table_args__ = (UniqueConstraint('moneda', 'fecha', 'origen', name='uix_cotizacion_diaria'),)

class RegistroTributario(AuditableMixin, TenantBase):
    """
    Libro histórico de Retenciones y Percepciones del Tenant.
    Base de datos centralizada para la generación de archivos posicionales TXT (DDJJ).
    """
    __tablename__ = "registro_tributario"

    id = Column(Integer, primary_key=True, index=True)
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id"), nullable=False)

    # Naturaleza del flujo fiscal
    clase_tributo = Column(String(20), nullable=False, index=True)
    tipo_impuesto = Column(String(50), nullable=False, index=True)
    jurisdiccion = Column(String(50), nullable=False, default="AFIP", index=True)

    # Datos del Sujeto Pasivo / Activo
    cuit_sujeto = Column(String(11), nullable=False, index=True)
    razon_social_sujeto = Column(String(255), nullable=False)

    # Origen del movimiento
    fecha_registro = Column(Date, nullable=False, index=True)
    comprobante_id = Column(Integer, nullable=True)
    asiento_id = Column(Integer, ForeignKey("asientos_contables.id"), nullable=True)

    # Campos obligatorios para aplicativos SIRE / SICORE / ARBA
    numero_comprobante_origen = Column(String(50), nullable=True)
    numero_certificado = Column(String(50), nullable=True, unique=True, index=True)

    # Matemática Fiscal Estricta
    base_imponible = Column(Numeric(15, 2), nullable=False)
    alicuota_aplicada = Column(Numeric(5, 2), nullable=False)
    monto_impuesto = Column(Numeric(15, 2), nullable=False)

    # Metadatos de control
    periodo_fiscal = Column(String(6), nullable=False, index=True)
    origen_alicuota = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # 🌟 FIX ENTERPRISE: Candado contra anulación de periodos ya exportados
    exportado_ddjj = Column(Boolean, default=False, nullable=False)
    fecha_exportacion = Column(DateTime(timezone=True), nullable=True)

    entidad = relationship("RazonSocialPropia")
    asiento = relationship("AsientoContable")

# INMUTABILIDAD CONTABLE
event.listen(AsientoContable, 'before_delete', prevent_financial_delete)
event.listen(LineaAsiento, 'before_delete', prevent_financial_delete)