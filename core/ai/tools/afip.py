import logging
import hashlib
import redis
from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig

from core.database.session import tenant_session_ctx, ai_readonly_session
from core.domains.comprobantes.service import comprobante_service
from core.domains.comprobantes.schemas import ComprobanteCreate, MonedaEnum
from core.services.cotizacion_service import cotizacion_service
from core.utils.enums import ClaseDocumento
from config.config import settings

logger = logging.getLogger("AI_TOOLS_AFIP")

class EmitirComprobanteInput(BaseModel):
    clase_documento: str = Field(
        ...,
        description="El tipo de comprobante a emitir. DEBE ser uno de estos valores exactos: 'FACTURA', 'REMITO', 'NOTA_CREDITO', 'NOTA_DEBITO', 'RECIBO'."
    )
    cuit_cliente: str = Field(..., description="El CUIT del cliente (11 dígitos, sin guiones).")
    monto_total: float = Field(..., description="El importe total bruto del comprobante. Si es un Remito sin valor, enviar 0.")
    condicion_fiscal: str = Field(
        ...,
        description="Condición fiscal del cliente. Valores permitidos: 'Responsable Inscripto', 'Monotributo', 'Exento', 'Consumidor Final'."
    )
    concepto: str = Field(..., description="Una breve descripción de lo que se está facturando o remitiendo.")
    razon_social: Optional[str] = Field(None, description="El nombre o razón social del cliente, si fue proporcionado.")
    comprobante_origen_id: Optional[int] = Field(
        None,
        description="CRÍTICO: ID interno del comprobante original. OBLIGATORIO si la clase_documento es 'NOTA_CREDITO' o 'NOTA_DEBITO'. Ignorar para Facturas o Remitos."
    )
    moneda: str = Field(
        "ARS",
        description="La moneda de la operación. Valores permitidos: 'ARS' o 'USD'. Si no se especifica, asuma 'ARS'."
    )

@tool("emitir_comprobante_afip", args_schema=EmitirComprobanteInput)
def tool_emitir_comprobante_afip(
    clase_documento: str,
    cuit_cliente: str,
    monto_total: float,
    condicion_fiscal: str,
    concepto: str,
    razon_social: Optional[str],
    comprobante_origen_id: Optional[int],
    moneda: str,
    config: RunnableConfig
) -> str:
    """
    Emite un Comprobante (Factura, Remito, Nota de Crédito, etc.) y lo asienta en la base de datos.
    ÚSALA SOLO cuando el usuario te confirme la clase de documento, el CUIT, el monto, la moneda, el concepto y, si corresponde, el comprobante de origen.
    """
    configurable = config.get("configurable", {})
    tenant_schema = configurable.get("tenant_schema")
    entidad_id = configurable.get("entidad_id")

    if not tenant_schema or not entidad_id:
        return "ERROR INTERNO: No se pudo inyectar el contexto de seguridad Multi-Tenant."

    try:
        clase_enum = ClaseDocumento(clase_documento.upper())
    except ValueError:
        return f"ERROR DE VALIDACIÓN: La clase de documento '{clase_documento}' no es válida. Debe ser FACTURA, REMITO, NOTA_CREDITO, NOTA_DEBITO o RECIBO."

    if clase_enum in [ClaseDocumento.NOTA_CREDITO, ClaseDocumento.NOTA_DEBITO] and not comprobante_origen_id:
        return "ERROR DE NEGOCIO: Para emitir una Nota de Crédito o Débito, DEBES especificar obligatoriamente el ID del comprobante que estás anulando o modificando (comprobante_origen_id)."

    try:
        moneda_enum = MonedaEnum(moneda.upper())
    except ValueError:
        return f"ERROR DE VALIDACIÓN: La moneda '{moneda}' no es válida. Debe ser ARS o USD."

    # 1. Escudo de Idempotencia (Contempla la moneda)
    try:
        payload_crudo = f"{cuit_cliente}_{monto_total}_{moneda_enum.value}_{concepto}_{clase_enum.value}_{comprobante_origen_id or ''}".lower().strip()
        payload_hash = hashlib.sha256(payload_crudo.encode('utf-8')).hexdigest()
        lock_key = f"idempotency:ai_tool:afip:{tenant_schema}:{payload_hash}"

        r_sync = redis.from_url(settings.REDIS_URL, decode_responses=True)
        if not r_sync.set(lock_key, "locked", nx=True, ex=900):
            logger.warning(f"🛑 [IDEMPOTENCIA] Ejecución duplicada bloqueada para {tenant_schema}. Hash: {payload_hash}")
            return f"ALERTA DE SEGURIDAD: Detecté que este {clase_enum.value} en {moneda_enum.value} exacto ya fue emitido hace instantes. Operación abortada."
    except Exception as e:
        logger.error(f"Fallo al conectar a Redis para candado de idempotencia: {e}")
        return "ERROR DE INFRAESTRUCTURA: No se pudo verificar la seguridad de la transacción. Intente nuevamente."

    logger.info(f"🤖 [TOOL] IA ejecutando {clase_enum.value} ({moneda_enum.value}) para CUIT {cuit_cliente} | Tenant: {tenant_schema}")

    try:
        with tenant_session_ctx(tenant_schema) as db_write:
            from core.database.models_tenant import PlanCuentas, RazonSocialPropia

            emisor = db_write.query(RazonSocialPropia).filter(RazonSocialPropia.id == entidad_id).first()
            if not emisor:
                r_sync.delete(lock_key)
                return "ERROR INTERNO: No se encontró el perfil de la empresa emisora."
            cuit_real = emisor.cuit

            cuenta_ventas = db_write.query(PlanCuentas).filter(PlanCuentas.codigo_sistema == "VENTAS").first()
            if not cuenta_ventas:
                r_sync.delete(lock_key)
                return "ERROR DE NEGOCIO: No existe la cuenta ancla 'VENTAS' en el plan de cuentas."

            # 🌟 FIX B2B: Uso del Oráculo Cambiario Real
            try:
                cotizacion_valor = cotizacion_service.obtener_cotizacion_oficial_segura(
                    db=db_write, moneda=moneda_enum.value, fecha_operacion=date.today()
                )
            except ValueError as ve:
                r_sync.delete(lock_key)
                return f"ERROR CAMBIARIO: {str(ve)}"

            cf_map = {
                "responsable inscripto": "RESPONSABLE_INSCRIPTO",
                "monotributo": "MONOTRIBUTO",
                "exento": "EXENTO",
                "consumidor final": "CONSUMIDOR_FINAL"
            }
            cf_limpia = cf_map.get(str(condicion_fiscal).lower(), "CONSUMIDOR_FINAL")

            comprobante_in = ComprobanteCreate(
                entidad_id=entidad_id,
                punto_venta=1,
                clase_documento=clase_enum,
                tipo_operacion="VENTA",
                numero=1,
                fecha_emision=datetime.utcnow().strftime("%Y-%m-%d"),
                cuit_emisor=cuit_real,
                cuit_receptor=cuit_cliente.replace("-", ""),
                razon_social_receptor=razon_social,
                condicion_fiscal_receptor=cf_limpia,
                moneda=moneda_enum,
                cotizacion=cotizacion_valor, # Inyección de la cotización real
                importe_total=Decimal(str(monto_total)),
                importe_neto_gravado=Decimal(str(monto_total)),
                cuenta_contable_id=cuenta_ventas.id,
                comprobante_origen_id=comprobante_origen_id
            )

            if comprobante_origen_id:
                resultado = comprobante_service.crear_comprobante_con_vinculo(
                    db=db_write,
                    comprobante_in=comprobante_in,
                    tenant_id=entidad_id,
                    usuario_id="AI_AGENT"
                )
            else:
                resultado = comprobante_service.emitir_y_guardar_comprobante(
                    db=db_write,
                    afip_client=None,
                    comprobante_in=comprobante_in,
                    tenant_id=entidad_id
                )
            comprobante_id = resultado.id

        return f"¡Éxito! El {clase_enum.value} en {moneda_enum.value} fue procesado correctamente. ID Interno: {comprobante_id}."

    except ValueError as ve:
        r_sync.delete(lock_key)
        return f"ERROR DE VALIDACIÓN: El sistema rechazó la información. Motivo: {str(ve)}"
    except Exception as e:
        r_sync.delete(lock_key)
        logger.error(f"Fallo en Tool emitir_comprobante_afip: {e}", exc_info=True)
        return f"ERROR AL EMITIR: El motor fiscal rechazó la operación. Motivo: {str(e)}"