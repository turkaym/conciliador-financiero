import logging
from decimal import Decimal
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import OperationalError

from core.database.models_tenant import (
    Comprobante, MovimientoTesoreria, CuentaTesoreria, ReglaAprendizaje
)
from core.tasks.accounting import generar_asiento_conciliacion
from core.matching.transactions import registrar_match_seguro
from core.utils.enums import TipoMovimientoTesoreria

logger = logging.getLogger("MATCHING_ENGINE")
logger.setLevel(logging.INFO)

BATCH_SIZE = 500

def run_advanced_matching(db: Session, tenant_id: str, entidad_id: int) -> int:
    """
    Motor Automático Determinista (Enterprise Level).
    Preparado para ingesta futura de IA. Solo ejecuta matches 1:1 matemáticamente perfectos.
    """

    todas_las_reglas = db.query(ReglaAprendizaje).filter(
        ReglaAprendizaje.activa == True,
        ReglaAprendizaje.entidad_id == entidad_id
    ).all()

    reglas_por_cuit = {}
    for regla in todas_las_reglas:
        reglas_por_cuit.setdefault(regla.cuit_asociado, []).append(regla)

    total_matches_creados = 0
    last_id = 0

    while True:
        pendientes = db.query(Comprobante).filter(
            Comprobante.entidad_id == entidad_id,
            Comprobante.estado.in_(["PENDIENTE", "EMITIDO", "PARCIALMENTE CONCILIADO"]),
            Comprobante.saldo_pendiente > 0,
            Comprobante.id > last_id
        ).order_by(Comprobante.id).limit(BATCH_SIZE).all()

        if not pendientes:
            break

        matches_en_lote = []

        for cbte_referencia in pendientes:
            last_id = cbte_referencia.id
            monto_buscado = abs(cbte_referencia.saldo_pendiente)
            tipo_mov_requerido = TipoMovimientoTesoreria.INGRESO if cbte_referencia.tipo_operacion == "VENTA" else TipoMovimientoTesoreria.EGRESO

            mov_match = None
            metodo = None
            score_final = 1.0

            # ====================================================================
            # TIER 1: Match Perfecto (Monto Exacto + Fecha Exacta)
            # ====================================================================
            mov_match = db.query(MovimientoTesoreria).join(CuentaTesoreria).filter(
                CuentaTesoreria.entidad_id == entidad_id,
                MovimientoTesoreria.anulado == False,
                MovimientoTesoreria.tipo == tipo_mov_requerido,
                MovimientoTesoreria.saldo_pendiente == monto_buscado, # 🌟 ESTRICTO: ==
                MovimientoTesoreria.fecha == cbte_referencia.fecha_emision,
                CuentaTesoreria.moneda == cbte_referencia.moneda
            ).first()

            if mov_match:
                metodo = "exact_amount_date"

            # ====================================================================
            # TIER 2: Match por Referencia (Monto Exacto + Nro Factura en el Banco)
            # ====================================================================
            if not mov_match:
                numero_str = str(cbte_referencia.numero)
                if len(numero_str) >= 4: # Evita colapsos de índice GIN con números cortos
                    mov_match = db.query(MovimientoTesoreria).join(CuentaTesoreria).filter(
                        CuentaTesoreria.entidad_id == entidad_id,
                        MovimientoTesoreria.anulado == False,
                        MovimientoTesoreria.tipo == tipo_mov_requerido,
                        MovimientoTesoreria.saldo_pendiente == monto_buscado, # 🌟 ESTRICTO: ==
                        CuentaTesoreria.moneda == cbte_referencia.moneda,
                        MovimientoTesoreria.concepto_crudo.ilike(f"%{numero_str}%")
                    ).first()

                    if mov_match:
                        metodo = "invoice_reference"
                        score_final = 0.95

            # ====================================================================
            # TIER 3: Match Semántico (Monto Exacto + Regla Aprendida)
            # ====================================================================
            if not mov_match:
                reglas = reglas_por_cuit.get(cbte_referencia.cuit_receptor, [])
                if reglas:
                    filtros = [MovimientoTesoreria.concepto_crudo.ilike(f"%{'%'.join(r.patron_concepto.split())}%") for r in reglas]
                    if filtros:
                        mov_match = db.query(MovimientoTesoreria).join(CuentaTesoreria).filter(
                            CuentaTesoreria.entidad_id == entidad_id,
                            MovimientoTesoreria.anulado == False,
                            MovimientoTesoreria.tipo == tipo_mov_requerido,
                            MovimientoTesoreria.saldo_pendiente == monto_buscado, # 🌟 ESTRICTO: ==
                            CuentaTesoreria.moneda == cbte_referencia.moneda,
                            or_(*filtros)
                        ).first()
                        if mov_match:
                            metodo = "learning_rule"
                            score_final = 0.90

            # ====================================================================
            # EJECUCIÓN TRANSACCIONAL Y BLOQUEO
            # ====================================================================
            if mov_match and metodo:
                try:
                    with db.begin_nested():
                        cbte_locks = db.query(Comprobante).filter(
                            Comprobante.id == cbte_referencia.id,
                            Comprobante.saldo_pendiente == monto_buscado # Aseguramos que nadie lo tocó
                        ).with_for_update(nowait=True).all()

                        mov_locks = db.query(MovimientoTesoreria).filter(
                            MovimientoTesoreria.id == mov_match.id,
                            MovimientoTesoreria.saldo_pendiente == monto_buscado # Aseguramos que nadie lo tocó
                        ).with_for_update(nowait=True).all()

                        if not cbte_locks or not mov_locks:
                            logger.info(f"⚠️ [CARRERA DETECTADA] Cbte o Mov alterado por otro proceso. Saltando.")
                            continue

                        match_id = registrar_match_seguro(
                            db, [cbte_locks[0].id], [mov_locks[0].id], score_final, metodo, tenant_id,
                            "SYSTEM_ENGINE", mov_locks[0].concepto_crudo if metodo == "invoice_reference" else None
                        )
                        if match_id:
                            matches_en_lote.append(match_id)
                except OperationalError:
                    logger.warning(f"🔒 [LOCK] Bloqueo de DB en Cbte {cbte_referencia.id} o Mov {mov_match.id}.")
                except Exception as e:
                    logger.error(f"Error matcheando Cbte {cbte_referencia.id}: {e}", exc_info=True)

        if matches_en_lote:
            try:
                db.commit()
                total_matches_creados += len(matches_en_lote)
                logger.info(f"💾 Lote procesado: {len(matches_en_lote)} matches automáticos guardados.")

                for m_id in matches_en_lote:
                    generar_asiento_conciliacion.apply_async(
                        kwargs={"tenant_id": tenant_id, "match_id": m_id},
                        queue='accounting_queue'
                    )
            except Exception as e:
                db.rollback()
                logger.error(f"💥 Fallo crítico al commitear el lote actual: {e}", exc_info=True)

    return total_matches_creados