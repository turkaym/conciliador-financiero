import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session, insert
from sqlalchemy.exc import SQLAlchemyError

from core.database.models_tenant import Comprobante, ComprobanteAsociado, ColaMensajesMuertos, LogAuditoria, OutboxEvent

logger = logging.getLogger("AUDITOR_FISCAL")

def ejecutar_auditoria_integral(db: Session, tenant_id: str):
    """Orquesta las verificaciones de integridad fiscal en el esquema del inquilino."""
    logger.info(f"🕵️‍♂️ [AUDITOR] Iniciando escaneo de integridad para {tenant_id}")
    try:
        _conciliar_notas_credito_huerfanas(db, tenant_id)
        _auditar_mensajes_muertos(db, tenant_id)
        _detectar_fugas_cae(db, tenant_id)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"❌ [AUDITOR] Falla transaccional auditando {tenant_id}: {e}")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ [AUDITOR] Error lógico crítico en {tenant_id}: {e}", exc_info=True)

def _conciliar_notas_credito_huerfanas(db: Session, tenant_id: str):
    ncs_huerfanas = db.query(Comprobante).filter(
        Comprobante.clase_documento == 'NOTA_CREDITO',
        Comprobante.comprobante_origen_id == None
    ).all()

    vinculadas = 0
    for nc in ncs_huerfanas:
        asociados = db.query(ComprobanteAsociado).filter(ComprobanteAsociado.comprobante_id == nc.id).all()

        for asoc in asociados:
            padre = db.query(Comprobante).filter(
                Comprobante.cuit_emisor == nc.cuit_emisor,
                Comprobante.tipo_cbte_afip == asoc.tipo_cbte_afip,
                Comprobante.punto_venta == asoc.punto_venta,
                Comprobante.numero == asoc.numero
            ).first()

            if padre:
                nc.comprobante_origen_id = padre.id

                # Conversión cruzada si hay mismatch de moneda
                if padre.moneda != nc.moneda:
                    importe_nc_ars = Decimal(str(nc.importe_total)) * Decimal(str(nc.cotizacion))
                    descuento = importe_nc_ars / Decimal(str(padre.cotizacion))
                else:
                    descuento = Decimal(str(nc.importe_total))

                padre.saldo_pendiente -= descuento
                logger.info(f"🔗 [AUDITOR] Conciliación retroactiva: NC {nc.numero} vinculada a Factura {padre.numero}")
                vinculadas += 1
                break

    if vinculadas > 0:
        logger.info(f"✨ [AUDITOR] Se resolvieron {vinculadas} Notas de Crédito desincronizadas en {tenant_id}.")

def _auditar_mensajes_muertos(db: Session, tenant_id: str):
    fallos_activos = db.query(ColaMensajesMuertos).filter(ColaMensajesMuertos.resuelto == False).all()
    if fallos_activos:
        logger.warning(f"⚠️ [AUDITOR] ALERTA: Existen {len(fallos_activos)} comprobantes en la DLQ de {tenant_id} requiriendo intervención.")

def _detectar_fugas_cae(db: Session, tenant_id: str):
    limite_tiempo = datetime.now(timezone.utc) - timedelta(hours=24)
    borradores_estancados = db.query(Comprobante).filter(
        Comprobante.estado == 'BORRADOR',
        Comprobante.created_at < limite_tiempo
    ).all()

    if borradores_estancados:
        logger.error(f"🚨 [AUDITOR] RIESGO FISCAL: {len(borradores_estancados)} comprobantes atascados sin CAE por más de 24hs en {tenant_id}.")

def procesar_outbox_auditoria(db: Session, tenant_id: str):
    """
    Patrón Outbox (Fase 7.5): Extrae eventos pendientes,
    consolida en Audit Trail y purga la cola temporal.
    """
    logger.debug(f"🧹 [OUTBOX] Iniciando barrido para {tenant_id}")

    # 1. Extraemos hasta 1000 eventos pendientes usando Row-Level Lock
    eventos_pendientes = db.query(OutboxEvent).filter(
        OutboxEvent.status == "PENDING"
    ).with_for_update(skip_locked=True).limit(1000).all()

    if not eventos_pendientes:
        return

    try:
        tenant_logs = []
        ids_a_borrar = []

        # 2. Formateamos y preparamos para inyección masiva
        for evento in eventos_pendientes:
            payload = evento.payload

            # Aseguramos el tipado correcto para los campos que pueden ser None o string
            entidad_id_val = payload.get("entidad_id")
            entidad_id_int = int(entidad_id_val) if entidad_id_val and str(entidad_id_val).isdigit() else 0

            tenant_logs.append({
                "entidad": payload.get("entidad", "UNKNOWN"),
                "entidad_id": entidad_id_int,
                "accion": payload.get("accion", "UNKNOWN"),
                "usuario_id": payload.get("usuario_id"),
                "ip_origen": payload.get("ip_origen"),
                "detalles": payload.get("detalles", "{}"),
                "hash_firma": payload.get("hash_firma")
            })
            ids_a_borrar.append(evento.id)

        # 3. Inyección O(1) en la tabla definitiva
        if tenant_logs:
            db.connection().execute(insert(LogAuditoria).values(tenant_logs))

        # 4. Eliminación de la cola temporal
        if ids_a_borrar:
            db.query(OutboxEvent).filter(OutboxEvent.id.in_(ids_a_borrar)).delete(synchronize_session=False)

        db.commit()
        logger.info(f"✅ [OUTBOX] {len(tenant_logs)} eventos forenses consolidados en {tenant_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ [OUTBOX] Fallo crítico consolidando eventos en {tenant_id}: {e}", exc_info=True)
        # Opcional: Marcar como FAILED si no queremos que vuelva a intentar infinitamente
        # db.query(OutboxEvent).filter(OutboxEvent.id.in_(ids_a_borrar)).update({"status": "FAILED"})
        # db.commit()

# Modificamos el orquestador general del auditor para que incluya esta nueva fase
def ejecutar_auditoria_integral(db: Session, tenant_id: str):
    """Orquesta las verificaciones de integridad fiscal en el esquema del inquilino."""
    logger.info(f"🕵️‍♂️ [AUDITOR] Iniciando escaneo de integridad para {tenant_id}")
    try:
        # 🌟 NUEVO: Consolidación rápida de logs
        procesar_outbox_auditoria(db, tenant_id)

        # Procesos pesados existentes
        _conciliar_notas_credito_huerfanas(db, tenant_id)
        _auditar_mensajes_muertos(db, tenant_id)
        _detectar_fugas_cae(db, tenant_id)

        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"❌ [AUDITOR] Falla transaccional auditando {tenant_id}: {e}")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ [AUDITOR] Error lógico crítico en {tenant_id}: {e}", exc_info=True)