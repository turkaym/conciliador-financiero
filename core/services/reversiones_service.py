import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from fastapi import HTTPException, status

from core.database.models.pagos import OrdenPago, LotePago, LotePagoDetalle
from core.database.models_tenant import Comprobante, MovimientoTesoreria
from core.database.models.tesoreria import CuentaTesoreria
from core.database.models.contabilidad import RegistroTributario
from core.utils.enums import EstadoOrdenPago, EstadoLotePago, EstadoComprobante

logger = logging.getLogger("REVERSIONES")

def _enum_name(val):
    return val.name if hasattr(val, 'name') else str(val)

class ReversionesService:

    def anular_orden_pago(
        self,
        db: Session,
        entidad_id: int,
        orden_id: int,
        user_id: str = "SYSTEM",
        user_role: str = "operador",
        umbral_aprobacion: float = 0.0
    ) -> OrdenPago:

        # Bloque 0: Adquisición de Candado de Fila (Prevención de Condición de Carrera)
        try:
            orden = db.query(OrdenPago).filter(
                OrdenPago.id == orden_id,
                OrdenPago.entidad_id == entidad_id
            ).with_for_update(nowait=True).first()
        except OperationalError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="La orden está siendo procesada por otra transacción concurrentemente. Intente nuevamente."
            )

        if not orden:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de Pago no encontrada.")

        if _enum_name(orden.estado_orden) == "ANULADA":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La orden ya se encuentra anulada.")

        detalles_lote = db.query(LotePagoDetalle).filter(LotePagoDetalle.orden_pago_id == orden.id).all()
        lote = None
        if detalles_lote and detalles_lote[0].lote_id:
            lote_id = detalles_lote[0].lote_id
            lote = db.query(LotePago).filter(LotePago.id == lote_id).with_for_update().first()

        # 1. Resurrección de la Deuda Original (La Factura)
        comprobantes_ids = [det.comprobante_id for det in detalles_lote if det.comprobante_id]
        if comprobantes_ids:
            facturas = db.query(Comprobante).filter(Comprobante.id.in_(comprobantes_ids)).with_for_update().all()
            facturas_map = {f.id: f for f in facturas}

            for det in detalles_lote:
                if det.comprobante_id and det.comprobante_id in facturas_map:
                    factura = facturas_map[det.comprobante_id]
                    factura.saldo_pendiente += det.monto_asignado_moneda_origen

                    if factura.saldo_pendiente >= factura.importe_total:
                        factura.estado = EstadoComprobante.EMITIDO.value
                    else:
                        factura.estado = EstadoComprobante.PARCIAL.value

        # 2. Reversión en Tesorería (El Extorno Contable puro se delega al banco_service)
        if lote and _enum_name(lote.estado_lote) in ["AUTHORIZED_FOR_PAYMENT", "PAID"] and lote.cuenta_tesoreria_id:
            from core.services.banco_service import banco_service

            movimiento_original = db.query(MovimientoTesoreria).join(CuentaTesoreria).filter(
                MovimientoTesoreria.referencia_externa == lote.codigo_lote,
                MovimientoTesoreria.cuenta_id == lote.cuenta_tesoreria_id,
                CuentaTesoreria.entidad_id == entidad_id,
                MovimientoTesoreria.anulado == False
            ).with_for_update().first()

            if movimiento_original:
                if abs(movimiento_original.saldo_pendiente) < abs(movimiento_original.monto):
                    db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bloqueo de Auditoría: El movimiento bancario ya fue conciliado. Deshaga el match en el módulo de Conciliación antes de anular."
                    )

                try:
                    banco_service.anular_movimiento(db=db, movimiento_id=movimiento_original.id)
                except Exception as trans_err:
                    db.rollback()
                    raise HTTPException(status_code=400, detail=f"Fallo al revertir tesorería y generar extornos: {str(trans_err)}")
            else:
                logger.warning(f"Movimiento huérfano o ya anulado para lote {lote.codigo_lote}.")

        # 3. 🌟 FIX ARQUITECTURA FISCAL (Fase 1.2): Candado AFIP
        registros_fiscales = db.query(RegistroTributario).filter(
            RegistroTributario.entidad_id == entidad_id,
            RegistroTributario.numero_comprobante_origen == orden.codigo_trazabilidad,
            RegistroTributario.is_active == True
        ).with_for_update().all()

        for reg in registros_fiscales:
            # Verificación estricta del candado fiscal
            if getattr(reg, 'exportado_ddjj', False) is True:
                db.rollback()
                fecha_str = reg.fecha_exportacion.strftime("%Y-%m-%d %H:%M") if reg.fecha_exportacion else "Desconocida"
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Bloqueo Fiscal (SICORE/SIRE): La retención {reg.clase_tributo} ya fue exportada a AFIP el {fecha_str}. Operación abortada para prevenir descuadre en la Declaración Jurada. Emita una Nota de Crédito."
                )

            # Solo si no está exportado, permitimos el borrado lógico
            reg.is_active = False

        # 4. Actualización del Estado de la OP (Saneamiento anti-Magic Strings Fase 2.3)
        orden.estado_orden = EstadoOrdenPago.ANULADA.value if hasattr(EstadoOrdenPago, 'ANULADA') else "ANULADA"
        orden.actualizado_por_id = user_id

        if lote:
            if len(lote.detalles) == 1:
                lote.estado_lote = EstadoLotePago.VOIDED.value if hasattr(EstadoLotePago, 'VOIDED') else "VOIDED"
            else:
                lote.monto_total_lote -= sum(d.monto_asignado_ars for d in detalles_lote)
            lote.actualizado_por_id = user_id

        db.commit()
        db.refresh(orden)

        logger.info(f"Orden {orden.codigo_trazabilidad} anulada exitosamente bajo normativas fiscales.")

        # 🌟 FIX ARQUITECTURA: Degradación elegante para el broker asíncrono
        try:
            from core.tasks.reversiones_tasks import task_notificar_anulacion

            task_notificar_anulacion.apply_async(
                kwargs={
                    "entidad_id": entidad_id,
                    "orden_id": orden.id,
                    "user_id": user_id
                }
            )
        except Exception as celery_err:
            logger.error(f"Fallo al encolar tarea asíncrona de notificación para OP {orden.id}. Transacción SQL completada. Error broker: {str(celery_err)}")

        return orden

reversiones_service = ReversionesService()