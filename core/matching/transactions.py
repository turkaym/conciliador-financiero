import logging
import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

# 🌟 FIX PEP 8: Centralización estricta de Modelos y Enums (Erradicación de Lazy Imports)
from core.utils.enums import ClaseDocumento, EstadoOrdenPago
from core.database.models.pagos import OrdenPago
from core.database.models_tenant import (
    Comprobante, MovimientoTesoreria, ConciliacionMatch,
    MatchDetalleComprobante, MatchDetalleMovimiento,
    LogAuditoria, ReglaAprendizaje, AsientoContable
)
from core.tasks.accounting import generar_asiento_conciliacion, revertir_asiento_conciliacion

logger = logging.getLogger("MATCHING_TRANSACTIONS")
logger.setLevel(logging.INFO)

def aprender_regla(db: Session, concepto: str, cbte: Comprobante, entidad_id: int):
    patron = concepto.upper().strip()
    patron = re.sub(r'\b\d{2}[/-]\d{2}[/-]\d{2,4}\b', '', patron)
    patron = re.sub(r'\b\d{11}\b', '', patron)
    patron = re.sub(r'\b[A-Z0-9]{8,}\b', '', patron)
    patron = re.sub(r'\b\d+\b', '', patron)
    patron = re.sub(r'\s+', ' ', patron).strip()

    if len(patron) < 2:
        return

    regla = db.query(ReglaAprendizaje).filter(
        ReglaAprendizaje.patron_concepto == patron,
        ReglaAprendizaje.entidad_id == entidad_id
    ).first()

    if regla:
        regla.frecuencia_uso += 1
        regla.updated_at = func.now()
    else:
        nueva_regla = ReglaAprendizaje(
            patron_concepto=patron,
            cuit_asociado=cbte.cuit_receptor,
            tipo_cbte_asociado=cbte.tipo_cbte_afip,
            frecuencia_uso=1,
            entidad_id=entidad_id
        )
        db.add(nueva_regla)

def registrar_match_seguro(
    db: Session,
    cbte_ids: List[int],
    mov_ids: List[int],
    score: float,
    metodo: str,
    tenant_id: str,
    usuario_id: str,
    concepto_asociado: Optional[str] = None,
    ajustes_fiscales: list = None,
    op_ids: List[int] = None
) -> Optional[int]:
    """Crea el Match N:M con materialización de OPs como Espejos Ledger y tipado criptográfico."""

    op_ids = op_ids or []
    cbtes = []

    if cbte_ids:
        cbtes = db.query(Comprobante).filter(Comprobante.id.in_(cbte_ids)).order_by(Comprobante.id).with_for_update().all()
        if len(cbtes) != len(cbte_ids):
            logger.warning("Error: No se encontraron todos los comprobantes regulares.")
            return None

    # 🌟 FIX ARQUITECTÓNICO: Si hay Órdenes de Pago, las materializamos en el Libro Mayor
    if op_ids:
        ops_db = db.query(OrdenPago).filter(OrdenPago.id.in_(op_ids)).with_for_update().all()
        if len(ops_db) != len(op_ids):
            logger.warning("Error: No se encontraron todas las ordenes de pago solicitadas.")
            return None

        for op in ops_db:
            # Creamos un Comprobante Espejo (Mirror) transitorio para asentar la lógica en Ledger
            nuevo_cbte_op = Comprobante(
                entidad_id=op.entidad_id,
                tipo_operacion="ORDEN_PAGO_MIRROR", # Marca de agua crítica para la reversión
                clase_documento=ClaseDocumento.FACTURA.name if hasattr(ClaseDocumento.FACTURA, 'name') else "FACTURA",
                punto_venta=0,
                numero=op.id, # El número oficia de Foreign Key dura hacia la OP real
                fecha_emision=op.created_at.date() if op.created_at else datetime.now(timezone.utc).date(),
                cuit_emisor="00000000000",
                cuit_receptor="00000000000",
                importe_neto=0.0,
                importe_iva=0.0,
                importe_tributos=0.0,
                importe_neto_gravado=0.0,
                importe_total=op.monto_estimado,
                saldo_pendiente=op.monto_estimado,
                es_saldo_a_favor=False,
                estado="PENDIENTE",
                moneda=op.moneda.value if hasattr(op.moneda, 'value') else str(op.moneda),
                cotizacion=op.tipo_cambio_estimado or Decimal("1.0"),
                is_active=True
            )
            db.add(nuevo_cbte_op)
            db.flush()

            estado_pagada = getattr(EstadoOrdenPago, 'PAGADA', list(EstadoOrdenPago)[-1])
            op.estado_orden = estado_pagada
            op.actualizado_por_id = usuario_id

            cbtes.append(nuevo_cbte_op)

    movs = db.query(MovimientoTesoreria).filter(MovimientoTesoreria.id.in_(mov_ids)).order_by(MovimientoTesoreria.id).with_for_update().all()

    if not cbtes or len(movs) != len(mov_ids):
        logger.warning("Error: No se encontraron todos los registros.")
        return None

    monedas_cbtes = {c.moneda for c in cbtes}
    monedas_movs = {m.moneda for m in movs}
    if len(monedas_cbtes) > 1 or len(monedas_movs) > 1 or monedas_cbtes != monedas_movs:
        logger.error(f"❌ [CRITICAL] Conflicto de denominación monetaria. Cbtes: {monedas_cbtes} | Movs: {monedas_movs}")
        raise ValueError("Bloqueo de Seguridad: No se permite conciliar documentos con distinta denominación monetaria.")

    total_deuda = sum(abs(c.saldo_pendiente) for c in cbtes)
    total_pago = sum(abs(m.saldo_pendiente) for m in movs)

    total_ajustes = Decimal('0.0')
    if ajustes_fiscales:
        total_ajustes = sum((Decimal(str(a.get('monto_impuesto', '0.0'))) for a in ajustes_fiscales), Decimal('0.0'))

    poder_de_pago_efectivo = total_pago + total_ajustes

    if total_deuda == 0 or total_pago == 0:
        return None

    nuevo_match = ConciliacionMatch(score=score, metodo=metodo)
    db.add(nuevo_match)
    db.flush()

    nuevos_detalles = []

    remanente_a_cubrir_deuda = min(total_deuda, poder_de_pago_efectivo)

    for c in cbtes:
        if remanente_a_cubrir_deuda <= 0: break
        aplicar = min(abs(c.saldo_pendiente), remanente_a_cubrir_deuda)
        nuevos_detalles.append(MatchDetalleComprobante(match_id=nuevo_match.id, comprobante_id=c.id, monto_aplicado=aplicar))

        if c.saldo_pendiente > 0:
            c.saldo_pendiente -= aplicar
        else:
            c.saldo_pendiente += aplicar

        c.estado = "CONCILIADO" if abs(c.saldo_pendiente) == 0 else "PARCIALMENTE CONCILIADO"
        remanente_a_cubrir_deuda -= aplicar

    remanente_a_asignar_pago = total_pago
    for m in movs:
        if remanente_a_asignar_pago <= 0: break
        aplicar = min(abs(m.saldo_pendiente), remanente_a_asignar_pago)

        monto_para_detalle = min(aplicar, total_deuda)
        if monto_para_detalle > 0:
            nuevos_detalles.append(MatchDetalleMovimiento(
                match_id=nuevo_match.id,
                movimiento_tesoreria_id=m.id,
                monto_aplicado=monto_para_detalle
            ))

        if m.saldo_pendiente > 0:
            m.saldo_pendiente -= aplicar
        else:
            m.saldo_pendiente += aplicar

        m.estado = "CONCILIADO" if abs(m.saldo_pendiente) == 0 else "PARCIALMENTE CONCILIADO"
        remanente_a_asignar_pago -= aplicar

    if nuevos_detalles:
        db.add_all(nuevos_detalles)

    excedente_real = total_pago - total_deuda
    if excedente_real > 0:
        logger.info(f"💸 [OVERPAYMENT] Creando Anticipo por ${excedente_real}.")

        today_local = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3))).date()

        anticipo = Comprobante(
            entidad_id=cbtes[0].entidad_id,
            tipo_operacion=cbtes[0].tipo_operacion,
            clase_documento=ClaseDocumento.RECIBO,
            punto_venta=0,
            numero=0,
            fecha_emision=today_local,
            cuit_emisor=cbtes[0].cuit_emisor,
            cuit_receptor=cbtes[0].cuit_receptor,
            importe_neto=0.0,
            importe_iva=0.0,
            importe_tributos=0.0,
            importe_neto_gravado=0.0,
            importe_total=excedente_real,
            saldo_pendiente=excedente_real,
            es_saldo_a_favor=True,
            estado="PENDIENTE",
            comprobante_origen_id=cbtes[0].id,
            moneda=cbtes[0].moneda,
            cotizacion=getattr(cbtes[0], 'cotizacion', 1.0)
        )
        db.add(anticipo)
        db.flush()

        db.add(MatchDetalleComprobante(
            match_id=nuevo_match.id,
            comprobante_id=anticipo.id,
            monto_aplicado=excedente_real
        ))

    if metodo in ["fuzzy_db_native", "manual_fix"] and concepto_asociado and len(cbtes) == 1:
        aprender_regla(db, concepto_asociado, cbtes[0], cbtes[0].entidad_id)

    payload = {
        "comprobantes_ids": cbte_ids,
        "op_ids": op_ids,
        "movimientos_ids": mov_ids,
        "monto_efectivo": "{:.2f}".format(total_pago),
        "ajustes_fiscales": ajustes_fiscales or [],
        "score": score,
        "metodo": metodo,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    payload_str = json.dumps(payload, sort_keys=True)
    firma = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()

    db.flush()

    log = LogAuditoria(
        entidad="ConciliacionMatch",
        entidad_id=nuevo_match.id,
        accion="MATCH_CONFIRMADO" if metodo == "manual_fix" else "MATCH_AUTOMATICO",
        usuario_id=str(usuario_id),
        ip_origen="internal",
        detalles=payload_str,
        hash_firma=firma
    )
    db.add(log)

    return nuevo_match.id

def force_manual_match(
    db: Session,
    tenant_id: str,
    comprobantes_ids: List[int],
    movimientos_ids: List[int],
    usuario_id: str,
    ajustes_fiscales: list = None,
    op_ids: List[int] = None
) -> bool:
    try:
        with db.begin_nested():
            match_id = registrar_match_seguro(
                db, comprobantes_ids, movimientos_ids, 1.0, "manual_fix", tenant_id, usuario_id, ajustes_fiscales=ajustes_fiscales, op_ids=op_ids
            )
            if not match_id:
                raise ValueError("Validación fallida: No se pudo generar el identificador del match.")

        db.commit()

        try:
            generar_asiento_conciliacion.apply_async(
                kwargs={"tenant_id": tenant_id, "match_id": match_id},
                queue='accounting_queue'
            )
        except Exception as cel_e:
            logger.critical(f"⚠️ [BROKER CAÍDO] Match {match_id} consolidado pero Asiento NO encolado: {cel_e}")

        return True

    except ValueError as ve:
        db.rollback()
        logger.error(f"Error de validación de negocio (API HTTP 400): {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    # 🌟 FIX DEUDA TÉCNICA: Captura explícita de errores SQL
    except SQLAlchemyError as sqle:
        db.rollback()
        logger.error(f"Fallo relacional al consolidar Match Manual: {sqle}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Fallo en base de datos al consolidar la operación.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error crítico en Match Manual: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Fallo sistémico al consolidar la operación.")

def ejecutar_reversion_segura(db: Session, tenant_id: str, match_id: int) -> bool:
    """Efectúa el Soft Delete del emparejamiento, restituyendo los saldos al Ledger unificado."""
    try:
        match = db.query(ConciliacionMatch).filter(ConciliacionMatch.id == match_id).with_for_update().first()
        if not match:
            return False

        for detalle_c in match.detalles_comprobantes:
            if detalle_c.comprobante:
                cae = getattr(detalle_c.comprobante, 'cae', None)
                if cae and str(cae).strip():
                    raise ValueError("Documento con validación fiscal ARCA/AFIP activa (CAE). Operación bloqueada. Emita la Nota de Crédito correspondiente.")

        ids_comprobantes_en_match = [d.comprobante_id for d in match.detalles_comprobantes]

        for detalle_c in match.detalles_comprobantes:
            if detalle_c.comprobante:

                # 🌟 FIX ARQUITECTÓNICO REVERSIÓN OP
                if detalle_c.comprobante.tipo_operacion == "ORDEN_PAGO_MIRROR":
                    op_id = detalle_c.comprobante.numero

                    op = db.query(OrdenPago).filter(OrdenPago.id == op_id).first()
                    if op:
                        estado_auth = getattr(EstadoOrdenPago, 'AUTORIZADA', list(EstadoOrdenPago)[0])
                        op.estado_orden = estado_auth

                    detalle_c.comprobante.estado = "ANULADO"
                    detalle_c.comprobante.is_active = False
                    continue

                es_anticipo = detalle_c.comprobante.es_saldo_a_favor
                creado_por_este_match = es_anticipo and (detalle_c.comprobante.comprobante_origen_id in ids_comprobantes_en_match)

                if creado_por_este_match:
                    if detalle_c.comprobante.saldo_pendiente != detalle_c.comprobante.importe_total:
                        logger.error(f"Integridad Comprometida: Anticipo {detalle_c.comprobante.id} ya consumido parcialmente.")
                        raise ValueError("El anticipo generado por esta conciliación ya fue utilizado en otra operación. Desconcilie las operaciones hijas primero.")

                    detalle_c.comprobante.estado = "ANULADO"
                    detalle_c.comprobante.is_active = False
                    continue

                if detalle_c.comprobante.importe_total >= 0:
                    detalle_c.comprobante.saldo_pendiente += detalle_c.monto_aplicado
                else:
                    detalle_c.comprobante.saldo_pendiente -= detalle_c.monto_aplicado

                detalle_c.comprobante.estado = "PENDIENTE" if abs(detalle_c.comprobante.saldo_pendiente) == abs(detalle_c.comprobante.importe_total) else "PARCIALMENTE CONCILIADO"

        for detalle_m in match.detalles_movimientos:
            if detalle_m.movimiento_tesoreria:
                detalle_m.movimiento_tesoreria.saldo_pendiente += detalle_m.monto_aplicado
                detalle_m.movimiento_tesoreria.estado = "PENDIENTE" if abs(detalle_m.movimiento_tesoreria.saldo_pendiente) == abs(detalle_m.movimiento_tesoreria.monto) else "PARCIALMENTE CONCILIADO"

        asiento_orig = db.query(AsientoContable).filter(AsientoContable.match_id == match.id).first()
        asiento_orig_id = asiento_orig.id if asiento_orig else None

        match.is_active = False
        db.commit()

        if asiento_orig_id:
            try:
                revertir_asiento_conciliacion.apply_async(
                    kwargs={"tenant_id": tenant_id, "asiento_original_id": asiento_orig_id},
                    queue='accounting_queue'
                )
            except Exception as cel_e:
                logger.critical(f"⚠️ [BROKER CAÍDO] Reversión de Match {match.id} consolidada pero Anulación de Asiento NO encolada: {cel_e}")

        return True

    except ValueError as ve:
        db.rollback()
        raise ve

    # 🌟 FIX DEUDA TÉCNICA: Captura explícita de errores SQL
    except SQLAlchemyError as sqle:
        db.rollback()
        logger.error(f"Fallo relacional en reversión de match: {sqle}", exc_info=True)
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"Error sistémico en reversión de match: {e}", exc_info=True)
        raise
