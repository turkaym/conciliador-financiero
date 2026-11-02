# ==========================================
# 🌟 FACADE ARQUITECTÓNICO (STRANGLER FIG PATTERN)
# ==========================================
# Este archivo actúa como un índice (Router). Permite que el resto del
# sistema siga importando desde "models_tenant" sin romperse,
# mientras que internamente la arquitectura ya está desacoplada por dominios (DDD).

from core.database.models.mixins import TenantBase, AuditableMixin
from core.database.models.entidades import RazonSocialPropia, UsuarioEntidadRol, ContactoComercial
from core.database.models.bancos import CuentaBancaria, MovimientoBancario, ConciliacionMatch, MatchDetalleComprobante, MatchDetalleMovimiento
from core.database.models.pagos import ConceptoOperativo, OrdenPago, LotePago, LotePagoDetalle
from core.database.models.contabilidad import ReglaAprendizaje, PlanCuentas, AsientoContable, LineaAsiento, PeriodoContable, HistorialCotizacion, ReglaImpuesto
from core.database.models.sistema import SecuenciaFiscal, ColaMensajesMuertos, PadronFiscal, ApiKey, WebhookSubscription, WebhookDeliveryLog, OutboxEvent, LogAuditoria
from core.domains.comprobantes.models import (
    Comprobante,
    ComprobanteIva,
    ComprobanteTributo,
    ComprobanteAsociado
)
from core.database.models.tesoreria import CuentaTesoreria, MovimientoTesoreria

# Exportamos todas las clases para que Alembic y Base.metadata.create_all() las registren globalmente.
__all__ = [
    "TenantBase",
    "AuditableMixin",
    "RazonSocialPropia",
    "UsuarioEntidadRol",
    "ContactoComercial",
    "CuentaBancaria",
    "MovimientoBancario",
    "ConciliacionMatch",
    "MatchDetalleComprobante",
    "MatchDetalleMovimiento",
    "ConceptoOperativo",
    "OrdenPago",
    "LotePago",
    "LotePagoDetalle",
    "ReglaAprendizaje",
    "PlanCuentas",
    "AsientoContable",
    "LineaAsiento",
    "PeriodoContable",
    "HistorialCotizacion",
    "SecuenciaFiscal",
    "ColaMensajesMuertos",
    "ReglaImpuesto",
    "PadronFiscal",
    "ApiKey",
    "WebhookSubscription",
    "WebhookDeliveryLog",
    "OutboxEvent",
    "LogAuditoria",
    "Comprobante",
    "ComprobanteIva",
    "CuentaTesoreria",
    "MovimientoTesoreria",
    "ComprobanteTributo",
    "ComprobanteAsociado"
]

# ==========================================
# 🌟 COMPILACIÓN DEL GRAFO ORM (SANEAMIENTO DE MEMORIA)
# ==========================================
from sqlalchemy.orm import configure_mappers
import logging

logger = logging.getLogger("ORM_INIT")

try:
    # Fuerza a SQLAlchemy a resolver todos los string-relationships inmediatamente.
    # Evita el lazy-loading en runtime y previene los warnings de "overlapping relationships".
    configure_mappers()
    logger.info("✅ Mappers ORM compilados exitosamente (Fuga de memoria sellada).")
except Exception as e:
    logger.critical(f"❌ Fallo crítico en el grafo de dependencias de SQLAlchemy: {e}")
    raise