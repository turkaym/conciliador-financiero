import logging
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, not_
from core.database.models_tenant import (
    Comprobante, CuentaTesoreria, MovimientoTesoreria,
    ConciliacionMatch, AsientoContable,
    MatchDetalleComprobante, MatchDetalleMovimiento
)
from core.database.models.pagos import OrdenPago
from core.utils.enums import ClaseDocumento, TipoMovimientoTesoreria

logger = logging.getLogger("REPORTS")

def _format_cbte(c) -> str:
    # Soporte polimórfico para Órdenes de Pago
    if isinstance(c, OrdenPago) or getattr(c, 'codigo_trazabilidad', None):
        return str(getattr(c, 'codigo_trazabilidad', f"OP-{c.id}"))

    afip_mapping = {
        1: "FC-A", 2: "ND-A", 3: "NC-A", 15: "REC-A",
        6: "FC-B", 7: "ND-B", 8: "NC-B", 16: "REC-B",
        11: "FC-C", 12: "ND-C", 13: "NC-C", 17: "REC-C",
        51: "FC-M", 52: "ND-M", 53: "NC-M", 54: "REC-M"
    }
    prefix = "CB"
    tipo_cbte = getattr(c, 'tipo_cbte_afip', None)
    clase_doc = getattr(c, 'clase_documento', None)
    pv = getattr(c, 'punto_venta', 0)
    num = getattr(c, 'numero', 0)

    if tipo_cbte and tipo_cbte in afip_mapping:
        prefix = afip_mapping[tipo_cbte]
    elif clase_doc:
        prefix = str(clase_doc)[:3].upper()
    else:
        prefix = "DOC"

    return f"{prefix} {pv:05d}-{num:08d}"

def get_unreconciled_data(db: Session, entidad_id: int, limit: int = 100, offset: int = 0):
    """
    🌟 ENTERPRISE REFACTOR: Extrae datos del Libro de Tesorería Unificado.
    Incorpora soporte polimórfico para Órdenes de Pago y aísla Extornos Internos.
    """

    # 1. Base Query Facturación Pendiente (Comprobantes)
    base_cbtes_query = db.query(Comprobante).filter(
        Comprobante.entidad_id == entidad_id,
        Comprobante.saldo_pendiente > 0,
        Comprobante.is_active == True,
        Comprobante.estado.in_(["PENDIENTE", "EMITIDO", "PARCIALMENTE CONCILIADO"])
    )

    cbtes_emitidos = base_cbtes_query.filter(
        Comprobante.clase_documento.in_([ClaseDocumento.FACTURA, ClaseDocumento.NOTA_DEBITO, ClaseDocumento.RECIBO]),
        Comprobante.tipo_operacion == "VENTA"
    ).order_by(Comprobante.fecha_emision.desc(), Comprobante.id.desc()).limit(limit).offset(offset).all()

    cbtes_recibidos = base_cbtes_query.filter(
        Comprobante.clase_documento.in_([ClaseDocumento.FACTURA, ClaseDocumento.NOTA_DEBITO, ClaseDocumento.RECIBO]),
        Comprobante.tipo_operacion == "COMPRA"
    ).order_by(Comprobante.fecha_emision.desc(), Comprobante.id.desc()).limit(limit).offset(offset).all()

    # 🌟 FIX ARQUITECTURA: Agregamos Base Query para Órdenes de Pago (Pasivos puros)
    from core.utils.enums import EstadoOrdenPago

    # Tolerancia a posibles variantes del enum en la db
    estados_op_validos = []
    if hasattr(EstadoOrdenPago, 'AUTORIZADA'): estados_op_validos.append(EstadoOrdenPago.AUTORIZADA)
    if hasattr(EstadoOrdenPago, 'PENDIENTE_PAGO'): estados_op_validos.append(EstadoOrdenPago.PENDIENTE_PAGO)

    # Si la lista queda vacía (por importación fallida del enum), forzamos un string por defecto
    if not estados_op_validos:
        estados_op_validos = ["AUTORIZADA", "PENDIENTE_PAGO"]

    ordenes_pago = db.query(OrdenPago).filter(
        OrdenPago.entidad_id == entidad_id,
        OrdenPago.estado_orden.in_(estados_op_validos)
    ).order_by(OrdenPago.created_at.desc()).limit(limit).offset(offset).all()

    # Uniformizamos la Orden de Pago para que el Frontend la entienda como Comprobante
    for op in ordenes_pago:
        # Hacemos duck-typing (override de atributos en tiempo de ejecución) para el serializer
        setattr(op, "tipo_registro", "ORDEN_PAGO")
        setattr(op, "saldo_pendiente", op.monto_estimado)
        setattr(op, "fecha_emision", op.created_at)
        setattr(op, "razon_social_receptor", getattr(op.proveedor, 'razon_social', "Proveedor S/D"))
        setattr(op, "clase_documento", "ORDEN DE PAGO")
        setattr(op, "tipo_operacion", "COMPRA")

    # Inyectamos las OPs a la lista de Comprobantes Recibidos (Columna Derecha de Pagos)
    cbtes_recibidos_unificados = cbtes_recibidos + ordenes_pago

    # 2. Base Query Movimientos Tesorería (El nuevo Ledger)
    base_movs_query = db.query(MovimientoTesoreria).join(CuentaTesoreria).filter(
        CuentaTesoreria.entidad_id == entidad_id,
        CuentaTesoreria.is_active == True,
        MovimientoTesoreria.anulado == False,
        MovimientoTesoreria.saldo_pendiente > 0,
        # 🌟 BARRERA DE AISLAMIENTO: Excluímos estrictamente los movimientos de extorno interno
        not_(MovimientoTesoreria.concepto_crudo.ilike('[EXTORNO]%'))
    )

    movs_ingresos = base_movs_query.filter(
        MovimientoTesoreria.tipo == TipoMovimientoTesoreria.INGRESO
    ).order_by(MovimientoTesoreria.fecha.desc(), MovimientoTesoreria.id.desc()).limit(limit).offset(offset).all()

    movs_egresos = base_movs_query.filter(
        MovimientoTesoreria.tipo == TipoMovimientoTesoreria.EGRESO
    ).order_by(MovimientoTesoreria.fecha.desc(), MovimientoTesoreria.id.desc()).limit(limit).offset(offset).all()

    # 3. Conteos Totales (Para la UI)
    total_cbtes_emitidos = db.query(func.count(Comprobante.id)).filter(
        Comprobante.entidad_id == entidad_id, Comprobante.saldo_pendiente > 0, Comprobante.is_active == True,
        Comprobante.estado.in_(["PENDIENTE", "EMITIDO", "PARCIALMENTE CONCILIADO"]), Comprobante.tipo_operacion == "VENTA"
    ).scalar() or 0

    total_cbtes_recibidos = db.query(func.count(Comprobante.id)).filter(
        Comprobante.entidad_id == entidad_id, Comprobante.saldo_pendiente > 0, Comprobante.is_active == True,
        Comprobante.estado.in_(["PENDIENTE", "EMITIDO", "PARCIALMENTE CONCILIADO"]), Comprobante.tipo_operacion == "COMPRA"
    ).scalar() or 0

    total_ops = db.query(func.count(OrdenPago.id)).filter(
        OrdenPago.entidad_id == entidad_id,
        OrdenPago.estado_orden.in_(estados_op_validos)
    ).scalar() or 0

    total_movs_ingresos = db.query(func.count(MovimientoTesoreria.id)).join(CuentaTesoreria).filter(
        CuentaTesoreria.entidad_id == entidad_id, CuentaTesoreria.is_active == True,
        MovimientoTesoreria.anulado == False, MovimientoTesoreria.saldo_pendiente > 0,
        not_(MovimientoTesoreria.concepto_crudo.ilike('[EXTORNO]%')), # 🌟 BARRERA DE AISLAMIENTO
        MovimientoTesoreria.tipo == TipoMovimientoTesoreria.INGRESO
    ).scalar() or 0

    total_movs_egresos = db.query(func.count(MovimientoTesoreria.id)).join(CuentaTesoreria).filter(
        CuentaTesoreria.entidad_id == entidad_id, CuentaTesoreria.is_active == True,
        MovimientoTesoreria.anulado == False, MovimientoTesoreria.saldo_pendiente > 0,
        not_(MovimientoTesoreria.concepto_crudo.ilike('[EXTORNO]%')), # 🌟 BARRERA DE AISLAMIENTO
        MovimientoTesoreria.tipo == TipoMovimientoTesoreria.EGRESO
    ).scalar() or 0

    return {
        "ar_cbtes": cbtes_emitidos,
        "ar_cbtes_count": total_cbtes_emitidos,
        "ar_movs": movs_ingresos,
        "ar_movs_count": total_movs_ingresos,

        # 🌟 Unificamos la suma para el reporte final del Dashboard
        "ap_cbtes": cbtes_recibidos_unificados,
        "ap_cbtes_count": total_cbtes_recibidos + total_ops,
        "ap_movs": movs_egresos,
        "ap_movs_count": total_movs_egresos
    }

def print_reconciliation_summary(db: Session, entidad_id: int):
    pass

def get_matched_history(db: Session, entidad_id: int, limit: int = 50, offset: int = 0):
    total_matches = db.query(func.count(ConciliacionMatch.id.distinct())).join(
        MatchDetalleComprobante
    ).join(
        Comprobante
    ).filter(
        Comprobante.entidad_id == entidad_id,
        ConciliacionMatch.is_active == True
    ).scalar() or 0

    matches = db.query(ConciliacionMatch).options(
        joinedload(ConciliacionMatch.asientos),
        joinedload(ConciliacionMatch.detalles_comprobantes).joinedload(MatchDetalleComprobante.comprobante),
        joinedload(ConciliacionMatch.detalles_movimientos).joinedload(MatchDetalleMovimiento.movimiento_tesoreria)
    ).join(
        MatchDetalleComprobante
    ).join(
        Comprobante
    ).filter(
        Comprobante.entidad_id == entidad_id,
        ConciliacionMatch.is_active == True
    ).order_by(ConciliacionMatch.id.desc()).limit(limit).offset(offset).all()

    resultados = []
    for m in matches:
        cbtes = [{
            # Garantizamos polimorfismo en el historial
            "id": f"CBT-{dc.comprobante_id}",
            "numero": dc.comprobante.numero,
            "numero_formateado": _format_cbte(dc.comprobante),
            "monto_total": float(dc.comprobante.importe_total),
            "monto_aplicado": float(dc.monto_aplicado)
        } for dc in m.detalles_comprobantes if dc.comprobante]

        movs = [{
            "id": dm.movimiento_tesoreria_id,
            "concepto": dm.movimiento_tesoreria.concepto_crudo if dm.movimiento_tesoreria else "S/D",
            "monto_total": float(abs(dm.movimiento_tesoreria.monto)) if dm.movimiento_tesoreria else 0,
            "monto_aplicado": float(dm.monto_aplicado)
        } for dm in m.detalles_movimientos if dm.movimiento_tesoreria]

        asiento_id = None
        if getattr(m, 'asientos', None) and len(m.asientos) > 0:
            asiento_id = m.asientos[0].id

        resultados.append({
            "id": m.id,
            "asiento_id": asiento_id,
            "score": float(m.score),
            "metodo": m.metodo,
            "comprobantes": cbtes,
            "movimientos": movs
        })

    return {
        "items": resultados,
        "total": total_matches,
        "limit": limit,
        "offset": offset
    }