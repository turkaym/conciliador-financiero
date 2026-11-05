from core.database.base import Base as MasterBase
from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, DateTime, Date, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database.models.mixins import TenantBase, AuditableMixin

# ==========================================
# CONFIGURACIÓN DE SISTEMA, DLQ Y WEBHOOKS
# ==========================================
class SecuenciaFiscal(TenantBase):
    __tablename__ = "secuencias_fiscales"

    id = Column(Integer, primary_key=True, index=True)
    # FIX: Se agrega la columna entidad_id para el mapeo ORM
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id", ondelete="CASCADE"), nullable=False)
    punto_venta = Column(Integer, nullable=False)
    tipo_cbte = Column(Integer, nullable=False)
    ultimo_numero = Column(Integer, default=0, nullable=False)

    # FIX: Se actualiza el UniqueConstraint para incluir la entidad (Aislamiento Multi-tenant)
    __table_args__ = (UniqueConstraint('entidad_id', 'punto_venta', 'tipo_cbte', name='uix_ptovta_tipocbte'),)

class ColaMensajesMuertos(AuditableMixin, TenantBase):
    __tablename__ = "cola_mensajes_muertos"

    id = Column(Integer, primary_key=True, index=True)
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id"), nullable=False)
    punto_venta = Column(Integer, nullable=False)
    tipo_cbte_afip = Column(Integer, nullable=False)
    numero = Column(Integer, nullable=False)

    error_msg = Column(Text, nullable=False)
    traceback = Column(Text, nullable=True)

    resuelto = Column(Boolean, default=False, nullable=False)
    resolved_by_id = Column(String(255), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    entidad = relationship("RazonSocialPropia")

class PadronFiscal(AuditableMixin, TenantBase):
    __tablename__ = "padrones_fiscales"

    # 🌟 FIX ARQUITECTÓNICO: Inyección de Entidad para Aislamiento Multi-Tenant
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    cuit = Column(String(11), primary_key=True, nullable=False)
    jurisdiccion = Column(String(50), primary_key=True, nullable=False)
    periodo = Column(String(6), primary_key=True, nullable=False)

    alicuota_retencion = Column(Numeric(7, 4), nullable=False, default=0.0)
    alicuota_percepcion = Column(Numeric(7, 4), nullable=False, default=0.0)
    coeficiente_riesgo = Column(Numeric(5, 2), nullable=True)

    entidad = relationship("RazonSocialPropia")

class ApiKey(TenantBase):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    prefix = Column(String(8), nullable=False, index=True)
    hashed_key = Column(String(128), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    entidad = relationship("RazonSocialPropia")
    __table_args__ = (UniqueConstraint('prefix', name='uix_api_key_prefix'),)

class WebhookSubscription(AuditableMixin, TenantBase):
    __tablename__ = "webhook_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(500), nullable=False)
    event_types = Column(JSON, nullable=False)
    secret = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    entidad = relationship("RazonSocialPropia")

class WebhookDeliveryLog(AuditableMixin, TenantBase):
    __tablename__ = "webhook_delivery_logs"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    is_successful = Column(Boolean, default=False, nullable=False)
    attempt_number = Column(Integer, default=1, nullable=False)

    subscription = relationship("WebhookSubscription")

class OutboxEvent(MasterBase):
    __tablename__ = "outbox_events"
    __table_args__ = {'schema': 'public'} # 🌟 FIX: Forzar la pertenencia al esquema maestro

    id = Column(Integer, primary_key=True, index=True)
    aggregate_type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), default="PENDING", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LogAuditoria(AuditableMixin, TenantBase):
    __tablename__ = "logs_auditoria"

    id = Column(Integer, primary_key=True, index=True)
    entidad = Column(String(50), nullable=False)
    entidad_id = Column(Integer, nullable=False)
    accion = Column(String(50), nullable=False)
    usuario_id = Column(String(255), nullable=True)
    ip_origen = Column(String(50), nullable=True)
    detalles = Column(Text, nullable=False)
    hash_firma = Column(String(64), nullable=False)

class HistorialIngestaPadron(AuditableMixin, TenantBase):
    """
    Bitácora física de telemetría para las ingestas masivas de Celery.
    Permite auditar el estado y resultado de la carga de Padrones de Riesgo.
    """
    __tablename__ = "historial_ingestas_padrones"

    id = Column(Integer, primary_key=True, index=True)
    entidad_id = Column(Integer, ForeignKey("razones_sociales_propias.id", ondelete="CASCADE"), nullable=False)

    # Metadatos del archivo
    jurisdiccion = Column(String(50), nullable=False, index=True) # ARBA, AGIP
    periodo = Column(String(6), nullable=False, index=True) # YYYYMM
    nombre_archivo = Column(String(255), nullable=False)

    # Telemetría
    estado = Column(String(20), nullable=False, default="PROCESANDO") # PROCESANDO, EXITO, FALLO
    registros_insertados = Column(Integer, default=0, nullable=False)
    mensaje_error = Column(Text, nullable=True)

    # Trazabilidad
    tarea_celery_id = Column(String(255), nullable=True, index=True)
    iniciado_el = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finalizado_el = Column(DateTime(timezone=True), nullable=True)

    entidad = relationship("RazonSocialPropia")