import logging
import traceback
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import OperationalError
from celery.exceptions import MaxRetriesExceededError

from core.tasks.celery_config import app
from core.database.session import get_tenant_db, SessionLocal
from core.database.models_tenant import (
    ConciliacionMatch, PlanCuentas, AsientoContable, LineaAsiento,
    MatchDetalleMovimiento, MatchDetalleComprobante
)
from core.database.models_master import SystemLog
from core.services.periodo_service import periodo_service
from core.database.session import tenant_session_ctx

logger = logging.getLogger("ACCOUNTING_ENGINE")

def registrar_falla_critica(tenant_id: str, operacion: str, referencia_id: int, error_msg: str, traceback_str: str):
    db_master = SessionLocal()
    try:
        log = SystemLog(
            level="CRITICAL",
            module="ACCOUNTING_WORKER",
            message=f"[{operacion}] Fallo definitivo para ID: {referencia_id}. Error: {error_msg}",
            details=traceback_str,
            tenant_reference=tenant_id
        )
        db_master.add(log)
        db_master.commit()
        logger.critical(f"🚨 Falla crítica registrada en SystemLog para {tenant_id} - Operación: {operacion}")
    except Exception as e:
        logger.error(f"Fallo extremo: No se pudo escribir la DLQ en SystemLog: {e}")
    finally:
        db_master.close()

def obtener_cuentas_base(db: Session) -> dict:
    anclas_requeridas = ["BANCOS", "VENTAS", "COMPRAS_GASTOS", "GASTOS_BANCARIOS", "DIF_CAMBIO_POS"]
    cuentas = db.query(PlanCuentas).filter(PlanCuentas.codigo_sistema.in_(anclas_requeridas)).all()

    mapa_cuentas = {c.codigo_sistema: c.id for c in cuentas}

    faltantes = set(anclas_requeridas) - set(mapa_cuentas.keys())
    if faltantes:
        raise ValueError(f"🚨 ROTURA DE CONFIGURACIÓN: Faltan las siguientes cuentas base en el Plan de Cuentas: {', '.join(faltantes)}.")

    return mapa_cuentas

def validar_partida_doble_estricta(lineas: list[LineaAsiento]):
    total_debe = sum(l.debe for l in lineas)
    total_haber = sum(l.haber for l in lineas)

    if total_debe != total_haber:
        raise ValueError(f"💥 ROTURA CONTABLE DETECTADA: Asiento descuadrado. Debe: {total_debe} | Haber: {total_haber}")

# =====================================================================
# 🌟 CORE FUNCTIONS
# =====================================================================

def generar_asiento_core(db: Session, match_id: int) -> int:
    # 🛡️ BARRERA DE IDEMPOTENCIA
    existente = db.query(AsientoContable).filter(AsientoContable.match_id == match_id).first()
    if existente:
        logger.warning(f"⚡ [IDEMPOTENCIA] El Match {match_id} ya posee el Asiento {existente.id}.")
        return existente.id

    match = db.query(ConciliacionMatch).options(
        # 🌟 FIX ARQUITECTURA: Apuntamos a la nueva relación 'movimiento_tesoreria'
        joinedload(ConciliacionMatch.detalles_movimientos).joinedload(MatchDetalleMovimiento.movimiento_tesoreria),
        joinedload(ConciliacionMatch.detalles_comprobantes).joinedload(MatchDetalleComprobante.comprobante)
    ).filter(ConciliacionMatch.id == match_id).first()

    if not match:
        raise ValueError(f"Match {match_id} no encontrado o ya fue borrado físicamente.")

    if not match.detalles_movimientos:
        raise ValueError(f"Match {match_id} no tiene movimientos bancarios asociados.")

    # 🌟 FIX ARQUITECTURA: Extraemos la fecha del nuevo Ledger Unificado
    primer_mov = match.detalles_movimientos[0].movimiento_tesoreria
    fecha_asiento = primer_mov.fecha

    periodo_service.verificar_periodo_abierto(db, fecha_asiento.year, fecha_asiento.month)

    total_pago_aplicado = Decimal(sum(abs(d.monto_aplicado) for d in match.detalles_movimientos))
    total_deuda_aplicada = Decimal(sum(abs(d.monto_aplicado) for d in match.detalles_comprobantes))

    # Evita explotar si es un match de $0 o Overpayment puro
    if total_pago_aplicado == 0 and total_deuda_aplicada == 0:
        logger.warning(f"Match {match_id} con montos aplicados en cero. Abortando generación de asiento.")
        return 0

    cuentas = obtener_cuentas_base(db)

    asiento = AsientoContable(
        fecha=fecha_asiento,
        concepto=f"Conciliación | Match ID: {match.id} | {len(match.detalles_comprobantes)} Cbtes vs {len(match.detalles_movimientos)} Movs",
        match_id=match.id
    )
    db.add(asiento)
    db.flush()

    delta = total_deuda_aplicada - total_pago_aplicado
    es_ingreso = sum(d.monto_aplicado for d in match.detalles_movimientos) > 0

    lineas = []

    if es_ingreso:
        if total_pago_aplicado > 0:
            lineas.append(LineaAsiento(asiento_id=asiento.id, cuenta_id=cuentas["BANCOS"], debe=total_pago_aplicado, haber=0))
        if total_deuda_aplicada > 0:
            lineas.append(LineaAsiento(asiento_id=asiento.id, cuenta_id=cuentas["VENTAS"], debe=0, haber=total_deuda_aplicada))

        if delta > 0:
            lineas.append(LineaAsiento(asiento_id=asiento.id, cuenta_id=cuentas["GASTOS_BANCARIOS"], debe=delta, haber=0))
        elif delta < 0:
            lineas.append(LineaAsiento(asiento_id=asiento.id, cuenta_id=cuentas["DIF_CAMBIO_POS"], debe=0, haber=abs(delta)))
    else:
        if total_deuda_aplicada > 0:
            lineas.append(LineaAsiento(asiento_id=asiento.id, cuenta_id=cuentas["COMPRAS_GASTOS"], debe=total_deuda_aplicada, haber=0))
        if total_pago_aplicado > 0:
            lineas.append(LineaAsiento(asiento_id=asiento.id, cuenta_id=cuentas["BANCOS"], debe=0, haber=total_pago_aplicado))

        if delta > 0:
            lineas.append(LineaAsiento(asiento_id=asiento.id, cuenta_id=cuentas["DIF_CAMBIO_POS"], debe=0, haber=delta))
        elif delta < 0:
            lineas.append(LineaAsiento(asiento_id=asiento.id, cuenta_id=cuentas["GASTOS_BANCARIOS"], debe=abs(delta), haber=0))

    if lineas:
        validar_partida_doble_estricta(lineas)
        db.add_all(lineas)
        db.flush()

    return asiento.id

def revertir_asiento_core(db: Session, asiento_original_id: int) -> int:
    asiento_orig = db.query(AsientoContable).options(
        joinedload(AsientoContable.lineas)
    ).filter(AsientoContable.id == asiento_original_id).first()

    if not asiento_orig:
        raise ValueError(f"Asiento original {asiento_original_id} no encontrado.")

    # 🛡️ BARRERA DE IDEMPOTENCIA REVERSA
    reversion_existente = db.query(AsientoContable).filter(
        AsientoContable.concepto == f"ANULACIÓN - {asiento_orig.concepto}"
    ).first()

    if reversion_existente:
        logger.warning(f"⚡ [IDEMPOTENCIA] El Asiento {asiento_original_id} ya posee reversión.")
        return reversion_existente.id

    periodo_service.verificar_periodo_abierto(db, asiento_orig.fecha.year, asiento_orig.fecha.month)

    asiento_rev = AsientoContable(
        fecha=asiento_orig.fecha,
        concepto=f"ANULACIÓN - {asiento_orig.concepto}",
        match_id=None # Huérfano para auditoría
    )
    db.add(asiento_rev)
    db.flush()

    lineas_rev = [LineaAsiento(
        asiento_id=asiento_rev.id, cuenta_id=lo.cuenta_id, debe=lo.haber, haber=lo.debe
    ) for lo in asiento_orig.lineas]

    validar_partida_doble_estricta(lineas_rev)

    if lineas_rev:
        db.add_all(lineas_rev)

    db.flush()
    return asiento_rev.id

# =====================================================================
# 🌟 CELERY WORKERS
# =====================================================================

@app.task(name="generar_asiento_conciliacion", bind=True, max_retries=3)
def generar_asiento_conciliacion(self, tenant_id: str, match_id: int):
    logger.info(f"⚖️ [MOTOR CONTABLE] Evaluando Match {match_id} en {tenant_id} (Modo N:M)")

    with tenant_session_ctx(tenant_id) as db:
        try:
            asiento_id = generar_asiento_core(db, match_id)
            db.commit()
            logger.info(f"✅ [MOTOR CONTABLE] Asiento {asiento_id} confirmado en DB.")
            return {"status": "success", "asiento_id": asiento_id}
        except ValueError as ve:
            db.rollback()
            logger.error(str(ve))
            return {"status": "error", "detail": str(ve)}
        except OperationalError as oe:
            db.rollback()
            logger.warning(f"⚠️ [MOTOR CONTABLE] Bloqueo temporal en BD, encolando reintento: {oe}")
            try:
                raise self.retry(exc=oe, countdown=5)
            except MaxRetriesExceededError:
                registrar_falla_critica(tenant_id, "GENERAR_ASIENTO", match_id, str(oe), traceback.format_exc())
                raise
        except Exception as exc:
            db.rollback()
            logger.error(f"❌ [MOTOR CONTABLE] Fallo inesperado: {exc}")
            try:
                raise self.retry(exc=exc, countdown=15)
            except MaxRetriesExceededError:
                registrar_falla_critica(tenant_id, "GENERAR_ASIENTO", match_id, str(exc), traceback.format_exc())
                raise

@app.task(name="revertir_asiento_conciliacion", bind=True, max_retries=3)
def revertir_asiento_conciliacion(self, tenant_id: str, asiento_original_id: int):
    logger.info(f"⏪ [MOTOR CONTABLE] Generando reversión para el Asiento {asiento_original_id}")

    with tenant_session_ctx(tenant_id) as db:
        try:
            asiento_rev_id = revertir_asiento_core(db, asiento_original_id)
            db.commit()
            logger.info(f"✅ [MOTOR CONTABLE] Reversión {asiento_rev_id} confirmada en DB.")
            return {"status": "success", "asiento_rev_id": asiento_rev_id}
        except ValueError as ve:
            db.rollback()
            return {"status": "error", "detail": str(ve)}
        except OperationalError as oe:
            db.rollback()
            try:
                raise self.retry(exc=oe, countdown=5)
            except MaxRetriesExceededError:
                registrar_falla_critica(tenant_id, "REVERTIR_ASIENTO", asiento_original_id, str(oe), traceback.format_exc())
                raise
        except Exception as exc:
            db.rollback()
            try:
                raise self.retry(exc=exc, countdown=15)
            except MaxRetriesExceededError:
                registrar_falla_critica(tenant_id, "REVERTIR_ASIENTO", asiento_original_id, str(exc), traceback.format_exc())
                raise