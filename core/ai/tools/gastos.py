import logging
import hashlib
import redis
from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig

from core.database.session import tenant_session_ctx
from core.domains.comprobantes.service import comprobante_service
from core.domains.comprobantes.schemas import ComprobanteCreate, MonedaEnum
from core.services.cotizacion_service import cotizacion_service
from core.utils.enums import ClaseDocumento
from config.config import settings

logger = logging.getLogger("AI_TOOLS_GASTOS")

class RegistrarGastoInput(BaseModel):
    cuit_proveedor: str = Field(..., description="El CUIT del proveedor o comercio (11 dígitos, sin guiones).")
    razon_social: Optional[str] = Field(None, description="Razón social o nombre del proveedor.")
    clase_documento: str = Field("FACTURA", description="Clase del documento. Valores: 'FACTURA' o 'RECIBO'.")
    punto_venta: int = Field(0, description="Punto de venta del ticket/factura del proveedor. Asumir 0 si es un gasto menor sin ticket.")
    numero_comprobante: int = Field(0, description="Número de comprobante del ticket/factura del proveedor. Asumir 0 si no hay ticket.")
    monto_total: float = Field(..., description="Monto total del gasto realizado.")
    concepto: str = Field(..., description="Descripción breve del gasto (ej: 'Nafta', 'Peaje', 'Viáticos').")
    cuenta_tesoreria_id: int = Field(..., description="ID interno de la caja o banco de donde salió el dinero. IMPORTANTE: Si no conocés este ID, usá primero la herramienta de consultar_entidad_financiera para listar las cuentas de TESORERIA.")
    moneda: str = Field("ARS", description="Moneda del gasto ('ARS' o 'USD').")

@tool("registrar_gasto_tesoreria", args_schema=RegistrarGastoInput)
def tool_registrar_gasto_tesoreria(
    cuit_proveedor: str,
    razon_social: Optional[str],
    clase_documento: str,
    punto_venta: int,
    numero_comprobante: int,
    monto_total: float,
    concepto: str,
    cuenta_tesoreria_id: int,
    moneda: str,
    config: RunnableConfig
) -> str:
    """
    Registra un comprobante de COMPRA (Gasto de proveedor) y descuenta los fondos automáticamente de la Tesorería.
    Úsala cuando el usuario reporte haber realizado un pago al contado, carga de combustible, caja chica, insumos, etc.
    """
    configurable = config.get("configurable", {})
    tenant_schema = configurable.get("tenant_schema")
    entidad_id = configurable.get("entidad_id")

    if not tenant_schema or not entidad_id:
        return "ERROR INTERNO: No se pudo inyectar el contexto de seguridad Multi-Tenant."

    try:
        clase_enum = ClaseDocumento(clase_documento.upper())
    except ValueError:
        clase_enum = ClaseDocumento.FACTURA

    try:
        moneda_enum = MonedaEnum(moneda.upper())
    except ValueError:
        return f"ERROR DE VALIDACIÓN: La moneda '{moneda}' no es válida. Debe ser ARS o USD."

    # 1. Escudo de Idempotencia para evitar descontar dos veces el mismo gasto
    try:
        payload_crudo = f"gasto_{cuit_proveedor}_{numero_comprobante}_{monto_total}_{cuenta_tesoreria_id}_{moneda_enum.value}".lower().strip()
        payload_hash = hashlib.sha256(payload_crudo.encode('utf-8')).hexdigest()
        lock_key = f"idempotency:ai_tool:gasto:{tenant_schema}:{payload_hash}"

        r_sync = redis.from_url(settings.REDIS_URL, decode_responses=True)
        if not r_sync.set(lock_key, "locked", nx=True, ex=900):
            logger.warning(f"🛑 [IDEMPOTENCIA] Gasto duplicado bloqueado para {tenant_schema}. Hash: {payload_hash}")
            return "ALERTA DE SEGURIDAD: Detecté que este mismo gasto exacto ya fue registrado hace instantes. Operación abortada."
    except Exception as e:
        logger.error(f"Fallo al conectar a Redis para candado de idempotencia: {e}")
        return "ERROR DE INFRAESTRUCTURA: No se pudo verificar la seguridad de la transacción. Intente nuevamente."

    logger.info(f"💸 [TOOL] IA registrando GASTO de ${monto_total} ({moneda_enum.value}) al CUIT {cuit_proveedor} | Tenant: {tenant_schema}")

    try:
        with tenant_session_ctx(tenant_schema) as db_write:
            from core.database.models_tenant import PlanCuentas, RazonSocialPropia

            emisor = db_write.query(RazonSocialPropia).filter(RazonSocialPropia.id == entidad_id).first()
            if not emisor:
                r_sync.delete(lock_key)
                return "ERROR INTERNO: No se encontró el perfil de la empresa receptora."

            # Buscamos la cuenta ancla para egresos
            cuenta_compras = db_write.query(PlanCuentas).filter(PlanCuentas.codigo_sistema.in_(["COMPRAS", "GASTOS"])).first()
            if not cuenta_compras:
                # Fallback extremo para asegurar el registro en MVP
                cuenta_compras = db_write.query(PlanCuentas).filter(PlanCuentas.imputable == True).first()
                if not cuenta_compras:
                    r_sync.delete(lock_key)
                    return "ERROR DE NEGOCIO: No existe ninguna cuenta imputable en el plan de cuentas para asentar este gasto."

            cotizacion_valor = Decimal('1.0')
            if moneda_enum == MonedaEnum.USD:
                try:
                    cotizacion_valor = cotizacion_service.obtener_cotizacion_oficial_segura(
                        db=db_write, moneda="USD", fecha_operacion=date.today()
                    )
                except ValueError as ve:
                    r_sync.delete(lock_key)
                    return f"ERROR CAMBIARIO: {str(ve)}"

            comprobante_in = ComprobanteCreate(
                entidad_id=entidad_id,
                punto_venta=punto_venta,
                numero=numero_comprobante,
                clase_documento=clase_enum,
                tipo_operacion="COMPRA",  # 🌟 CRÍTICO: Indica que recibimos la factura
                fecha_emision=datetime.utcnow().strftime("%Y-%m-%d"),
                cuit_emisor=cuit_proveedor.replace("-", ""), # El proveedor emite
                cuit_receptor=emisor.cuit, # Nosotros recibimos
                razon_social_receptor=razon_social, # Se inyecta al CRM
                condicion_fiscal_receptor="CONSUMIDOR_FINAL", # Fallback default
                moneda=moneda_enum,
                cotizacion=cotizacion_valor,
                importe_total=Decimal(str(monto_total)),
                importe_neto_gravado=Decimal(str(monto_total)),
                cuenta_contable_id=cuenta_compras.id,
                condicion_venta="CONTADO",         # 🌟 Obliga al sistema a descontar fondos
                cuenta_tesoreria_id=cuenta_tesoreria_id  # 🌟 De dónde sale la plata
            )

            # Para compras, NO instanciamos afip_client
            resultado = comprobante_service.emitir_y_guardar_comprobante(
                db=db_write,
                afip_client=None,
                comprobante_in=comprobante_in,
                tenant_id=entidad_id
            )
            comprobante_id = resultado.id

        return f"¡Éxito! El gasto fue registrado correctamente y los fondos se descontaron de la caja/banco. ID de Operación: {comprobante_id}."

    except ValueError as ve:
        r_sync.delete(lock_key)
        return f"ERROR DE VALIDACIÓN: El sistema rechazó la información. Motivo: {str(ve)}"
    except Exception as e:
        r_sync.delete(lock_key)
        logger.error(f"Fallo en Tool registrar_gasto_tesoreria: {e}", exc_info=True)
        return f"ERROR AL REGISTRAR: El motor contable rechazó la operación. Motivo: {str(e)}"