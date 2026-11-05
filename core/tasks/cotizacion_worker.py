import logging
import requests
from datetime import date
from decimal import Decimal, InvalidOperation
from sqlalchemy.dialects.postgresql import insert
from celery.exceptions import MaxRetriesExceededError

from core.tasks.celery_config import app
from core.database.session import tenant_session_ctx
from core.database.models_tenant import HistorialCotizacion

logger = logging.getLogger("WORKER_COTIZACION")

# 🌟 ARQUITECTURA DESACOPLADA: Adaptador externo aislado
def _fetch_cotizacion_bna_dolar() -> dict:
    """
    Adaptador HTTP para obtener la cotización oficial.
    Tolerancia Cero a Deadlocks: Timeout estricto de 10 segundos.
    """
    try:
        # Nota: En producción, esto apuntará al WSFE de AFIP o a la API del BNA.
        # Utilizamos una API pública confiable como fallback/ejemplo para el MVP.
        response = requests.get("https://dolarapi.com/v1/dolares/oficial", timeout=10.0)
        response.raise_for_status()
        data = response.json()

        return {
            "compra": Decimal(str(data.get("compra", 0))),
            "venta": Decimal(str(data.get("venta", 0)))
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Fallo de red contactando al proveedor de cotizaciones: {e}")
        raise ValueError("Servicio de cotizaciones inaccesible")
    except (InvalidOperation, TypeError, ValueError) as e:
        logger.error(f"❌ Dirty Data: El proveedor devolvió formatos numéricos inválidos: {e}")
        raise ValueError("Datos de cotización corruptos")

@app.task(bind=True, max_retries=5)
def sincronizar_cotizacion_diaria(self, tenant_id: str, moneda: str = "USD", origen: str = "BNA"):
    """
    Worker asíncrono para ingestar la cotización diaria.
    Resiliencia Nivel 3: UPSERT nativo + Backoff Exponencial + Fallback de Contingencia.
    """
    fecha_hoy = date.today()
    logger.info(f"🔄 Iniciando sincronización de {moneda} para tenant {tenant_id} ({fecha_hoy})...")

    try:
        # 1. Fetch de datos (I/O intensivo, fuera de la transacción de base de datos)
        cotizacion = _fetch_cotizacion_bna_dolar()

        if cotizacion["venta"] <= Decimal('0.0'):
            raise ValueError("La cotización de venta no puede ser cero o negativa.")

        # 2. Inyección en Base de Datos (Transacción ultra-corta)
        with tenant_session_ctx(tenant_id) as db:
            # 🌟 IDEMPOTENCIA ESTRICTA: Sentencia INSERT ... ON CONFLICT DO UPDATE
            stmt = insert(HistorialCotizacion).values(
                moneda=moneda,
                fecha=fecha_hoy,
                cotizacion_compra=cotizacion["compra"],
                cotizacion_venta=cotizacion["venta"],
                origen=origen
            )

            stmt = stmt.on_conflict_do_update(
                index_elements=['moneda', 'fecha', 'origen'],
                set_={
                    'cotizacion_compra': stmt.excluded.cotizacion_compra,
                    'cotizacion_venta': stmt.excluded.cotizacion_venta
                }
            )

            db.execute(stmt)
            db.commit()

            logger.info(f"✅ Sincronización exitosa: {moneda} Venta -> {cotizacion['venta']}")
            return {"status": "success", "moneda": moneda, "venta": str(cotizacion["venta"]), "origen": origen}

    except Exception as e:
        try:
            # 🌟 RESILIENCIA: Backoff exponencial real (2s, 4s, 8s, 16s...)
            logger.warning(f"⚠️ Fallo temporal contactando al proveedor. Encolando reintento {self.request.retries + 1}/{self.max_retries}")
            raise self.retry(exc=e, countdown=2 ** self.request.retries)

        except MaxRetriesExceededError:
            # 🌟 CIRCUIT BREAKER & FALLBACK: Se agotaron los reintentos. Salvar el negocio.
            logger.critical(f"🔥 Proveedor de moneda caído permanentemente. Activando protocolo de contingencia para {moneda}.")

            with tenant_session_ctx(tenant_id) as db:
                # Buscar la última cotización conocida (oficial o estimada previa)
                ultima_cot_conocida = db.query(HistorialCotizacion).filter(
                    HistorialCotizacion.moneda == moneda,
                    HistorialCotizacion.origen.like(f"{origen}%") # Atrapa "BNA" y "BNA_ESTIMADO"
                ).order_by(HistorialCotizacion.fecha.desc()).first()

                if not ultima_cot_conocida:
                    logger.error(f"💀 Fallback fallido: No existe historial previo para {moneda}. Negocio bloqueado.")
                    return {"status": "error", "detail": "Proveedor caído y sin historial previo."}

                # Inyectar clon de contingencia
                origen_estimado = f"{origen}_ESTIMADO"
                stmt_fallback = insert(HistorialCotizacion).values(
                    moneda=moneda,
                    fecha=fecha_hoy,
                    cotizacion_compra=ultima_cot_conocida.cotizacion_compra,
                    cotizacion_venta=ultima_cot_conocida.cotizacion_venta,
                    origen=origen_estimado
                )

                stmt_fallback = stmt_fallback.on_conflict_do_update(
                    index_elements=['moneda', 'fecha', 'origen'],
                    set_={
                        'cotizacion_compra': stmt_fallback.excluded.cotizacion_compra,
                        'cotizacion_venta': stmt_fallback.excluded.cotizacion_venta
                    }
                )
                db.execute(stmt_fallback)
                db.commit()

                logger.info(f"🛡️ Contingencia activada: Se arrastró cotización de {ultima_cot_conocida.fecha} para facturar hoy.")
                return {"status": "fallback", "moneda": moneda, "venta": str(ultima_cot_conocida.cotizacion_venta), "origen": origen_estimado}